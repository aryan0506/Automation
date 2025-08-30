import time
import random
import os
import sys
import shutil
import logging
import psutil
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import google.generativeai as genai

class YouTubeFeedOptimizer:
    def __init__(self, gemini_api_key):
        self.setup_logging()
        self.setup_gemini(gemini_api_key)
        self.setup_driver()
        self.api_call_count = 0
        self.last_api_call = 0
        self.premium_searches_done = set()
        
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
    def setup_gemini(self, api_key):
        self.logger.info("Setting up Gemini API")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def kill_chrome_processes(self):
        """Kill existing Chrome processes using the profile"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'youtube_optimizer_profile' in cmdline:
                        self.logger.info(f"Killing Chrome process {proc.info['pid']}")
                        proc.kill()
                        time.sleep(1)
        except Exception as e:
            self.logger.warning(f"Could not kill Chrome processes: {e}")
    
    def setup_driver(self):
        self.logger.info("Setting up Chrome driver")
        
        # Profile directory setup
        profile_dir = os.path.abspath("./youtube_optimizer_profile")
        
        # Kill existing Chrome processes using this profile
        self.kill_chrome_processes()
        
        # Clean up lock files if they exist
        lock_files = [
            os.path.join(profile_dir, "SingletonLock"),
            os.path.join(profile_dir, "Default", "SingletonLock"),
            os.path.join(profile_dir, "lockfile")
        ]
        
        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    self.logger.info(f"Removed lock file: {lock_file}")
                except:
                    pass
        
        os.makedirs(profile_dir, exist_ok=True)
        
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument(f"--user-data-dir={profile_dir}")
        
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Try initialization with multiple fallbacks
        driver_initialized = False
        
        # Method 1: webdriver-manager
        if not driver_initialized:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                driver_initialized = True
                self.logger.info("Chrome initialized with webdriver-manager")
            except Exception as e:
                self.logger.warning(f"webdriver-manager failed: {e}")
        
        # Method 2: system Chrome
        if not driver_initialized:
            try:
                self.driver = webdriver.Chrome(options=options)
                driver_initialized = True
                self.logger.info("Chrome initialized with system driver")
            except Exception as e:
                self.logger.warning(f"System Chrome failed: {e}")
        
        # Method 3: fallback without profile
        if not driver_initialized:
            try:
                self.logger.info("Trying fallback without profile...")
                options_fallback = Options()
                options_fallback.add_argument("--no-sandbox")
                options_fallback.add_argument("--disable-dev-shm-usage")
                options_fallback.add_argument("--disable-gpu")
                self.driver = webdriver.Chrome(options=options_fallback)
                driver_initialized = True
                self.logger.info("Chrome initialized without profile (fallback)")
            except Exception as e:
                self.logger.error(f"All methods failed: {e}")
                raise Exception("Could not initialize Chrome driver")
        
        if driver_initialized:
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.profile_dir = profile_dir
    
    def rate_limit_protection(self):
        """Implement rate limiting to avoid API throttling"""
        current_time = time.time()
        
        # Gemini API free tier: 15 requests per minute
        if self.api_call_count >= 10:  # Conservative limit
            time_since_first_call = current_time - self.last_api_call
            if time_since_first_call < 60:  # Within 1 minute
                sleep_time = 60 - time_since_first_call + 5  # Extra 5 seconds buffer
                self.logger.info(f"Rate limit protection: sleeping {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                self.api_call_count = 0
        
        self.api_call_count += 1
        self.last_api_call = current_time
        
    def analyze_video_content(self, title, channel):
        # Rate limiting protection
        self.rate_limit_protection()
        
        prompt = f"""Rate this YouTube content from 1-10 for educational/productivity value:
Title: {title}
Channel: {channel}

SPECIAL BONUS SCORING:
- Premium course content available free on YouTube: 10/10
- Paid tutorial/masterclass content shared free: 9-10/10
- Professional skills training normally behind paywall: 9-10/10

REGULAR SCORING:
- Educational tutorials, documentaries, skill-building: 7-8/10
- News, tech reviews with learning value: 6-7/10
- Entertainment with some educational aspect: 5-6/10
- Clickbait, drama, mindless content: 1-4/10

Look for keywords like: "full course", "masterclass", "complete tutorial", "premium", "paid course free", "bootcamp", "certification"

Respond with just a number 1-10."""
        
        try:
            response = self.model.generate_content(prompt)
            score_text = response.text.strip()
            score = int(''.join(filter(str.isdigit, score_text))[:1] or '5')
            return max(1, min(10, score)), score_text
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            # Exponential backoff on API errors
            time.sleep(random.uniform(5, 10))
            return 5, "Analysis failed"
    
    def search_premium_content(self, search_terms):
        """Search for premium content and interact with results"""
        if search_terms in self.premium_searches_done:
            return
            
        self.premium_searches_done.add(search_terms)
        
        try:
            self.logger.info(f"Searching for premium content: {search_terms}")
            
            # Multiple search box selectors
            search_selectors = [
                "input#search",
                "input[name='search_query']",
                "input[placeholder*='Search']",
                "#search-input input",
                "ytd-searchbox input",
                "#container input[type='text']"
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except:
                    continue
            
            if not search_box:
                self.logger.warning("Could not find search box")
                return
            
            # Clear and search
            search_box.clear()
            search_box.send_keys(search_terms)
            search_box.send_keys(Keys.RETURN)
            time.sleep(4)
            
            # Get search results with multiple selectors
            result_selectors = [
                "ytd-video-renderer",
                "ytd-rich-item-renderer",
                ".ytd-item-section-renderer > div"
            ]
            
            search_results = []
            for selector in result_selectors:
                try:
                    results = self.driver.find_elements(By.CSS_SELECTOR, selector)[:3]
                    if results:
                        search_results = results
                        break
                except:
                    continue
            
            if not search_results:
                self.logger.warning("No search results found")
                return
            
            # Process search results
            for result in search_results:
                try:
                    # Multiple title selectors for search results
                    title_selectors = [
                        "#video-title",
                        "h3 a",
                        "a#video-title-link",
                        ".ytd-video-meta-block h3 a"
                    ]
                    
                    title_elem = None
                    title = None
                    
                    for selector in title_selectors:
                        try:
                            title_elem = result.find_element(By.CSS_SELECTOR, selector)
                            title = title_elem.get_attribute("title") or title_elem.text
                            if title and title.strip():
                                break
                        except:
                            continue
                    
                    if not title:
                        continue
                    
                    # Check if it's premium content
                    premium_keywords = ['full course', 'complete', 'masterclass', 'free course', 'bootcamp', 'certification', 'tutorial series']
                    if any(keyword in title.lower() for keyword in premium_keywords):
                        self.logger.info(f"Found premium content: {title[:50]}...")
                        
                        # Click the video
                        self.driver.execute_script("arguments[0].click();", title_elem)
                        time.sleep(4)
                        
                        # Try to like the video
                        like_selectors = [
                            "button[aria-label*='like']",
                            "ytd-toggle-button-renderer:first-child button",
                            "#segmented-like-button button"
                        ]
                        
                        for selector in like_selectors:
                            try:
                                like_btn = WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                                like_btn.click()
                                self.logger.info("Liked premium content")
                                time.sleep(2)
                                break
                            except:
                                continue
                        
                        # Go back to home
                        self.driver.get("https://www.youtube.com")
                        time.sleep(3)
                        return
                        
                except Exception as e:
                    self.logger.debug(f"Error processing search result: {e}")
                    continue
            
            # Return to home page
            self.driver.get("https://www.youtube.com")
            time.sleep(3)
            
        except Exception as e:
            self.logger.error(f"Premium search failed: {e}")
            # Return to home on any error
            try:
                self.driver.get("https://www.youtube.com")
                time.sleep(3)
            except:
                pass
    
    def get_video_elements(self):
        try:
            WebDriverWait(self.driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-rich-item-renderer")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-video-renderer")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-reel-item-renderer"))
                )
            )
            
            elements = []
            elements.extend(self.driver.find_elements(By.CSS_SELECTOR, "ytd-rich-item-renderer"))
            elements.extend(self.driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer"))
            elements.extend(self.driver.find_elements(By.CSS_SELECTOR, "ytd-reel-item-renderer"))
            
            return elements
        except Exception as e:
            self.logger.error(f"Failed to get video elements: {e}")
            return []
    
    def extract_video_info(self, video_element):
        try:
            title_selectors = [
                "#video-title",
                "h3 a",
                ".ytd-reel-item-renderer h3",
                "[aria-label*='title']",
                "a#video-title-link"
            ]
            
            channel_selectors = [
                "#text > a",
                ".ytd-channel-name a",
                "#channel-name a",
                "[href*='/channel/']",
                "[href*='/@']"
            ]
            
            title = None
            title_elem = None
            
            for selector in title_selectors:
                try:
                    title_elem = video_element.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.get_attribute("title") or title_elem.get_attribute("aria-label") or title_elem.text
                    if title and title.strip():
                        break
                except:
                    continue
            
            channel = None
            for selector in channel_selectors:
                try:
                    channel_elem = video_element.find_element(By.CSS_SELECTOR, selector)
                    channel = channel_elem.text or channel_elem.get_attribute("aria-label")
                    if channel and channel.strip():
                        break
                except:
                    continue
            
            if not title:
                try:
                    all_text = video_element.text
                    lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                    if lines:
                        title = lines[0][:100]
                except:
                    pass
            
            if not channel:
                channel = "Unknown Channel"
            
            if title and title.strip():
                return title.strip(), channel.strip(), title_elem
            else:
                return None, None, None
                
        except Exception as e:
            return None, None, None
    
    def interact_with_video(self, video_element, action):
        try:
            if action == "like":
                title_selectors = ["#video-title", "h3 a", "a#video-title-link"]
                clicked = False
                
                for selector in title_selectors:
                    try:
                        title_elem = video_element.find_element(By.CSS_SELECTOR, selector)
                        self.driver.execute_script("arguments[0].click();", title_elem)
                        clicked = True
                        break
                    except:
                        continue
                
                if not clicked:
                    return
                
                time.sleep(3)
                
                like_selectors = [
                    "button[aria-label*='like']",
                    "ytd-toggle-button-renderer:first-child button",
                    "#segmented-like-button button"
                ]
                
                for selector in like_selectors:
                    try:
                        like_btn = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        like_btn.click()
                        break
                    except:
                        continue
                
                time.sleep(1)
                self.driver.back()
                time.sleep(2)
                
            elif action == "not_interested":
                self.driver.execute_script("arguments[0].scrollIntoView();", video_element)
                time.sleep(1)
                
                menu_selectors = [
                    "button[aria-label='Action menu']",
                    "button[aria-label*='More actions']",
                    ".ytd-menu-renderer button"
                ]
                
                menu_clicked = False
                for selector in menu_selectors:
                    try:
                        menu_btn = video_element.find_element(By.CSS_SELECTOR, selector)
                        menu_btn.click()
                        menu_clicked = True
                        break
                    except:
                        continue
                
                if not menu_clicked:
                    return
                
                time.sleep(1)
                
                not_interested_selectors = [
                    "//span[contains(text(), 'Not interested')]",
                    "//span[contains(text(), 'Don\\'t recommend')]"
                ]
                
                for selector in not_interested_selectors:
                    try:
                        not_interested = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        not_interested.click()
                        break
                    except:
                        continue
                
                time.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Interaction failed: {e}")
    
    def check_login_status(self):
        try:
            login_indicators = [
                "button[aria-label*='Account menu']",
                "#avatar-btn",
                "ytd-topbar-menu-button-renderer"
            ]
            
            for selector in login_indicators:
                try:
                    WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    return True
                except:
                    continue
            return False
        except:
            return False
    
    def optimize_feed(self, max_videos=15):
        self.logger.info("Opening YouTube...")
        self.driver.get("https://www.youtube.com")
        time.sleep(5)
        
        if self.check_login_status():
            self.logger.info("Already logged in! Starting optimization...")
        else:
            self.logger.info("Please log into YouTube manually")
            input("Press Enter after logging in...")
        
        # Search for premium content first
        premium_searches = [
            "free full course programming",
            "complete masterclass free"
        ]
        
        for search_term in premium_searches:
            self.search_premium_content(search_term)
            time.sleep(5)
        
        processed = 0
        scroll_count = 0
        processed_elements = set()
        
        while processed < max_videos and scroll_count < 15:
            videos = self.get_video_elements()
            print(f"Found {len(videos)} video elements")
            
            new_videos_found = False
            
            for video in videos:
                if processed >= max_videos:
                    break
                
                video_id = id(video)
                if video_id in processed_elements:
                    continue
                
                processed_elements.add(video_id)
                new_videos_found = True
                    
                title, channel, title_elem = self.extract_video_info(video)
                if not title or len(title.strip()) < 5:
                    continue
                
                print(f"\nAnalyzing: {title[:60]}...")
                print(f"Channel: {channel}")
                
                score, reason = self.analyze_video_content(title, channel)
                print(f"Score: {score}/10")
                
                # Special handling for premium content
                if score == 10:
                    print("🎯 PREMIUM CONTENT - Liking and engaging!")
                    self.interact_with_video(video, "like")
                elif score >= 7:
                    print("✓ High quality - Liking video")
                    self.interact_with_video(video, "like")
                elif score <= 4:
                    print("✗ Low quality - Marking not interested")
                    self.interact_with_video(video, "not_interested")
                else:
                    print("~ Neutral - No action")
                
                processed += 1
                
                # Longer delay after API calls to avoid rate limiting
                time.sleep(random.uniform(3, 6))
            
            if not new_videos_found:
                print("No new videos found, scrolling...")
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            scroll_count += 1
        
        print(f"\nProcessed {processed} videos")
        print(f"API calls made: {self.api_call_count}")
    
    def close(self):
        self.logger.info("Closing browser")
        try:
            self.driver.quit()
        except:
            pass

def main():
    try:
        from config import GEMINI_API_KEY
    except:
        GEMINI_API_KEY = "your_gemini_api_key_here"
    
    if GEMINI_API_KEY == "your_gemini_api_key_here":
        print("Please update GEMINI_API_KEY in config.py")
        return
    
    optimizer = YouTubeFeedOptimizer(GEMINI_API_KEY)
    
    try:
        print("Starting YouTube feed optimization...")
        optimizer.optimize_feed(max_videos=15)
        
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        optimizer.close()

if __name__ == "__main__":
    main()