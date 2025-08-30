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
import requests
import json

class YouTubeFeedOptimizer:
    def __init__(self, config):
        self.config = config
        self.setup_logging()
        self.setup_llm()
        self.setup_driver()
        self.api_call_count = 0
        self.last_api_call = 0
        self.premium_searches_done = set()
        self.generated_searches = []
        
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
    def setup_llm(self):
        """Setup LLM providers based on configuration"""
        self.logger.info(f"Setting up LLM provider: {self.config.LLM_PROVIDER}")
        
        # Setup Gemini if needed
        if self.config.LLM_PROVIDER in ["gemini", "both"]:
            try:
                genai.configure(api_key=self.config.GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                self.logger.info("Gemini API configured successfully")
            except Exception as e:
                self.logger.error(f"Gemini setup failed: {e}")
                if self.config.LLM_PROVIDER == "gemini":
                    raise Exception("Gemini setup failed and no fallback configured")
        
        # Setup Ollama if needed
        if self.config.LLM_PROVIDER in ["ollama", "both"]:
            try:
                # Test Ollama connection
                response = requests.get(f"{self.config.OLLAMA_BASE_URL}/api/tags", timeout=5)
                if response.status_code == 200:
                    self.logger.info("Ollama API connected successfully")
                else:
                    raise Exception(f"Ollama API returned status {response.status_code}")
            except Exception as e:
                self.logger.error(f"Ollama setup failed: {e}")
                if self.config.LLM_PROVIDER == "ollama":
                    raise Exception("Ollama setup failed and no fallback configured")
    
    def call_ollama_api(self, prompt):
        """Call Ollama API for text generation"""
        try:
            payload = {
                "model": self.config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 150
                }
            }
            
            response = requests.post(
                f"{self.config.OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Ollama API call failed: {e}")
            raise
    
    def call_gemini_api(self, prompt):
        """Call Gemini API for text generation"""
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            self.logger.error(f"Gemini API call failed: {e}")
            raise
    
    def generate_elite_search_terms(self):
        """Generate intelligent search terms using LLM"""
        if len(self.generated_searches) >= 5:  # Limit to avoid too many searches
            return []
            
        prompt = """Generate 2 highly specific YouTube search terms to find TOP 1% elite content in:
- Advanced skill mastery (not basic tutorials)
- Wealth building strategies from successful entrepreneurs
- Health optimization from medical experts
- Productivity systems from peak performers
- Mental models from world-class thinkers

Focus on:
- Content normally behind paywalls
- Expert-level insights
- Advanced methodologies
- Exclusive knowledge

Return only 2 search terms, one per line, no explanations."""

        try:
            if self.config.LLM_PROVIDER == "gemini":
                response = self.call_gemini_api(prompt)
            elif self.config.LLM_PROVIDER == "ollama":
                response = self.call_ollama_api(prompt)
            elif self.config.LLM_PROVIDER == "both":
                try:
                    response = self.call_gemini_api(prompt)
                except:
                    response = self.call_ollama_api(prompt)
            
            # Parse response into search terms
            search_terms = [term.strip() for term in response.split('\n') if term.strip()][:2]
            self.generated_searches.extend(search_terms)
            return search_terms
            
        except Exception as e:
            self.logger.error(f"Failed to generate search terms: {e}")
            return []
    
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
        
        # Rate limiting for Gemini API
        if self.config.LLM_PROVIDER in ["gemini", "both"]:
            if self.api_call_count >= 10:  # Conservative limit
                time_since_first_call = current_time - self.last_api_call
                if time_since_first_call < 60:  # Within 1 minute
                    sleep_time = 60 - time_since_first_call + 5  # Extra 5 seconds buffer
                    self.logger.info(f"Rate limit protection: sleeping {sleep_time:.1f} seconds")
                    time.sleep(sleep_time)
                    self.api_call_count = 0
        
        self.api_call_count += 1
        self.last_api_call = current_time
        
    def analyze_video_content(self, title, channel, duration=None, views=None, description=None):
        """Analyze video content using enhanced metadata and strict criteria"""
        # Rate limiting protection
        self.rate_limit_protection()
        
        # Build context with available metadata
        context = f"Title: {title}\nChannel: {channel}"
        if duration:
            context += f"\nDuration: {duration}"
        if views:
            context += f"\nViews: {views}"
        if description:
            context += f"\nDescription: {description[:200]}..."
        
        prompt = f"""Analyze this YouTube content for ELITE educational/productivity value:

{context}

STRICT SCORING CRITERIA (Rate 1-10):

🏆 TIER 1 (9-10/10) - WORLD-CLASS ELITE:
- Billionaire/CEO sharing actual business strategies
- Medical doctors/PhDs sharing advanced knowledge
- Premium courses ($500+) available free
- Advanced technical skills (programming, finance, etc.)
- Proven experts with real credentials

🎯 TIER 2 (7-8/10) - HIGH-VALUE PROFESSIONAL:
- Successful entrepreneurs with track record
- Professional certification content
- Advanced tutorials requiring prior knowledge
- Evidence-based health/fitness optimization
- Productivity systems from high achievers

⚡ TIER 3 (5-6/10) - DECENT LEARNING:
- General educational content
- Basic skill tutorials with good structure
- Informative news/analysis

❌ TIER 4 (1-4/10) - LOW VALUE:
- Music videos, songs, entertainment
- Clickbait, drama, gossip, reactions
- Mindless content, memes, shorts
- Basic lifestyle vlogs
- Gaming content (unless educational)

CRITICAL RULES:
- Music/songs = automatic 1-3/10 (entertainment, not educational)
- Entertainment content = 1-4/10 maximum
- Look for ACTUAL expertise and credentials
- Prioritize actionable, advanced knowledge
- Consider video length (longer often = more depth)

Respond with: SCORE|REASON
Example: 8|Advanced programming tutorial from Google engineer with 10+ years experience
Example: 2|Music video - pure entertainment with no educational value"""
        
        # Try primary provider first
        if self.config.LLM_PROVIDER == "gemini":
            return self._analyze_with_gemini(prompt)
        elif self.config.LLM_PROVIDER == "ollama":
            return self._analyze_with_ollama(prompt)
        elif self.config.LLM_PROVIDER == "both":
            # Try Gemini first, fallback to Ollama
            try:
                return self._analyze_with_gemini(prompt)
            except Exception as e:
                self.logger.warning(f"Gemini failed, trying Ollama: {e}")
                return self._analyze_with_ollama(prompt)
    
    def _analyze_with_gemini(self, prompt):
        """Analyze using Gemini API"""
        try:
            response_text = self.call_gemini_api(prompt)
            return self._parse_analysis_response(response_text)
        except Exception as e:
            self.logger.error(f"Gemini analysis failed: {e}")
            time.sleep(random.uniform(5, 10))
            raise
    
    def _analyze_with_ollama(self, prompt):
        """Analyze using Ollama API"""
        try:
            response_text = self.call_ollama_api(prompt)
            return self._parse_analysis_response(response_text)
        except Exception as e:
            self.logger.error(f"Ollama analysis failed: {e}")
            time.sleep(random.uniform(2, 5))
            raise
    
    def _parse_analysis_response(self, response_text):
        """Parse the LLM response to extract score and reason"""
        try:
            if '|' in response_text:
                parts = response_text.split('|', 1)
                score_text = parts[0].strip()
                reason = parts[1].strip() if len(parts) > 1 else "No reason provided"
            else:
                score_text = response_text.strip()
                reason = "Analysis completed"
            
            # Extract numeric score
            score = int(''.join(filter(str.isdigit, score_text))[:1] or '5')
            score = max(1, min(10, score))
            
            return score, reason
        except Exception as e:
            self.logger.error(f"Failed to parse analysis response: {e}")
            return 5, "Parsing failed"
    
    def search_premium_content(self, search_terms):
        """Search for premium content and interact with results"""
        if search_terms in self.premium_searches_done:
            return
            
        self.premium_searches_done.add(search_terms)
        
        try:
            self.logger.info(f"Searching for elite content: {search_terms}")
            
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
                    
                    # Check if it's elite content using enhanced keywords
                    elite_keywords = [
                        'masterclass', 'full course', 'complete guide', 'advanced', 'expert',
                        'billionaire', 'millionaire', 'ceo secrets', 'insider', 'exclusive',
                        'harvard', 'stanford', 'mit', 'phd', 'professor', 'research',
                        'optimization', 'biohacking', 'longevity', 'peak performance',
                        'mental models', 'frameworks', 'systems', 'strategies'
                    ]
                    
                    if any(keyword in title.lower() for keyword in elite_keywords):
                        self.logger.info(f"Found elite content: {title[:50]}...")
                        
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
                                self.logger.info("Liked elite content")
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
            self.logger.error(f"Elite search failed: {e}")
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
        """Extract comprehensive video information including metadata"""
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
            
            # Extract title
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
            
            # Extract channel
            channel = None
            for selector in channel_selectors:
                try:
                    channel_elem = video_element.find_element(By.CSS_SELECTOR, selector)
                    channel = channel_elem.text or channel_elem.get_attribute("aria-label")
                    if channel and channel.strip():
                        break
                except:
                    continue
            
            # Extract duration
            duration = None
            duration_selectors = [
                ".ytd-thumbnail-overlay-time-status-renderer",
                "#overlays .badge-shape-wiz__text",
                "span.style-scope.ytd-thumbnail-overlay-time-status-renderer"
            ]
            
            for selector in duration_selectors:
                try:
                    duration_elem = video_element.find_element(By.CSS_SELECTOR, selector)
                    duration = duration_elem.text.strip()
                    if duration:
                        break
                except:
                    continue
            
            # Extract view count
            views = None
            view_selectors = [
                "#metadata-line span:first-child",
                ".inline-metadata-item:first-child",
                "span[aria-label*='views']"
            ]
            
            for selector in view_selectors:
                try:
                    views_elem = video_element.find_element(By.CSS_SELECTOR, selector)
                    views = views_elem.text.strip()
                    if 'view' in views.lower():
                        break
                except:
                    continue
            
            # Fallback for title
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
                return {
                    'title': title.strip(),
                    'channel': channel.strip(),
                    'duration': duration,
                    'views': views,
                    'title_elem': title_elem
                }
            else:
                return None
                
        except Exception as e:
            return None
    
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
        
        # Generate intelligent search terms using LLM
        print("🧠 Generating elite search terms using AI...")
        elite_searches = self.generate_elite_search_terms()
        
        if elite_searches:
            print(f"🎯 Generated searches: {elite_searches}")
            for search_term in elite_searches:
                self.search_premium_content(search_term)
                time.sleep(5)
        else:
            print("⚠️ Using fallback searches...")
            fallback_searches = ["advanced wealth building strategies", "elite productivity systems"]
            for search_term in fallback_searches:
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
                    
                video_info = self.extract_video_info(video)
                if not video_info or len(video_info['title'].strip()) < 5:
                    continue
                
                print(f"\nAnalyzing: {video_info['title'][:60]}...")
                print(f"Channel: {video_info['channel']}")
                if video_info['duration']:
                    print(f"Duration: {video_info['duration']}")
                if video_info['views']:
                    print(f"Views: {video_info['views']}")
                
                try:
                    score, reason = self.analyze_video_content(
                        video_info['title'], 
                        video_info['channel'],
                        video_info['duration'],
                        video_info['views']
                    )
                    
                    print(f"💡 Reason: {reason}")
                    
                    # Enhanced feedback based on elite scoring
                    if score >= 9:
                        print(f"🏆 ELITE TIER 1 ({score}/10) - World-class content!")
                        self.interact_with_video(video, "like")
                    elif score >= 7:
                        print(f"🎯 HIGH-VALUE ({score}/10) - Professional level content")
                        self.interact_with_video(video, "like")
                    elif score >= 5:
                        print(f"⚡ DECENT ({score}/10) - Some learning value")
                        print("~ Neutral - No action")
                    else:
                        print(f"❌ LOW-VALUE ({score}/10) - Time waster")
                        self.interact_with_video(video, "not_interested")
                        
                except Exception as e:
                    print(f"❌ Analysis failed: {e}")
                    print("~ Skipping video")
                
                processed += 1
                
                # Longer delay after API calls to avoid rate limiting
                time.sleep(random.uniform(*self.config.ACTION_DELAY))
            
            if not new_videos_found:
                print("No new videos found, scrolling...")
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.config.SCROLL_DELAY)
            scroll_count += 1
        
        print(f"\nProcessed {processed} videos")
        print(f"API calls made: {self.api_call_count}")
        print(f"Elite searches generated: {len(self.generated_searches)}")
    
    def close(self):
        self.logger.info("Closing browser")
        try:
            self.driver.quit()
        except:
            pass

def main():
    # Import configuration
    try:
        import config
        print(f"Using LLM Provider: {config.LLM_PROVIDER}")
    except ImportError:
        print("Please create config.py file with your settings")
        return
    
    # Validate configuration
    if config.LLM_PROVIDER in ["gemini", "both"] and config.GEMINI_API_KEY == "your_gemini_api_key_here":
        print("Please update GEMINI_API_KEY in config.py")
        return
    
    optimizer = YouTubeFeedOptimizer(config)
    
    try:
        print("Starting YouTube feed optimization...")
        optimizer.optimize_feed(max_videos=config.MAX_VIDEOS_TO_PROCESS)
        
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        optimizer.close()

if __name__ == "__main__":
    main()