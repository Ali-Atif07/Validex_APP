# server/captcha_handler.py - Modified server with CAPTCHA handling
from datetime import datetime
from flask import Flask, request, jsonify
import base64
import time
import threading
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Enhanced session manager with CAPTCHA support
class CaptchaSessionManager:
    def __init__(self):
        self.sessions = {}
        self.captcha_requests = {}  # Store pending CAPTCHA requests
    
    def create_session(self, data):
        session_id = str(uuid.uuid4())
        session_data = {
            'sessionId': session_id,
            'status': 'initializing',
            'progress': 0,
            'driver': None,  # Store browser instance
            'captcha_pending': False,
            'captcha_image': None,
            **data
        }
        self.sessions[session_id] = session_data
        return session_data
    
    def set_captcha_pending(self, session_id, captcha_image_base64):
        if session_id in self.sessions:
            self.sessions[session_id].update({
                'status': 'captcha_required',
                'captcha_pending': True,
                'captcha_image': captcha_image_base64,
                'captcha_timestamp': time.time()
            })
    
    def submit_captcha_solution(self, session_id, solution):
        if session_id in self.sessions:
            self.sessions[session_id].update({
                'captcha_solution': solution,
                'captcha_pending': False,
                'status': 'processing_captcha'
            })
            return True
        return False

session_manager = CaptchaSessionManager()

def take_captcha_screenshot(driver, captcha_element=None):
    """Take screenshot of CAPTCHA area"""
    try:
        if captcha_element:
            # Screenshot just the CAPTCHA element
            captcha_png = captcha_element.screenshot_as_png
        else:
            # Full page screenshot
            captcha_png = driver.get_screenshot_as_png()
        
        # Convert to base64
        captcha_base64 = base64.b64encode(captcha_png).decode('utf-8')
        return captcha_base64
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None

def wait_for_captcha_solution(session_id, timeout=300):  # 5 minutes timeout
    """Wait for user to solve CAPTCHA via mobile app"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        session = session_manager.get_session(session_id)
        if not session:
            return None
        
        if not session.get('captcha_pending') and session.get('captcha_solution'):
            solution = session['captcha_solution']
            # Clear the solution
            session['captcha_solution'] = None
            return solution
        
        time.sleep(1)  # Check every second
    
    return None  # Timeout

def automate_foscos_with_captcha(session_id, license_number):
    """Modified automation with CAPTCHA handling"""
    try:
        session_manager.update_session(session_id, status='starting_browser', progress=5)
        
        # Setup headless Chrome
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=options)
        
        # Store driver in session for cleanup
        session_manager.sessions[session_id]['driver'] = driver
        
        session_manager.update_session(session_id, status='navigating', progress=10)
        
        # Navigate to FoSCoS
        driver.get("https://foscos.fssai.gov.in")
        time.sleep(3)
        
        # Fill license number (same as before)
        session_manager.update_session(session_id, status='filling_form', progress=20)
        
        # Find and click FBO Search tab
        fbo_tab = driver.find_element(By.XPATH, "//a[@id='governmentAgencies1']")
        driver.execute_script("arguments[0].click();", fbo_tab)
        time.sleep(2)
        
        # Fill license input
        license_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='License/Registration No.']"))
        )
        license_input.clear()
        license_input.send_keys(license_number)
        
        session_manager.update_session(session_id, status='handling_captcha', progress=30)
        
        # Handle CAPTCHA
        try:
            captcha_image = driver.find_element(By.XPATH, "//img[@alt='Captcha']")
            captcha_input = driver.find_element(By.XPATH, "//input[@placeholder='Enter Captcha Code']")
            
            # Take screenshot of CAPTCHA
            captcha_screenshot = take_captcha_screenshot(driver, captcha_image)
            
            if captcha_screenshot:
                # Send CAPTCHA to mobile app
                session_manager.set_captcha_pending(session_id, captcha_screenshot)
                
                # Wait for user to solve CAPTCHA
                print(f"Waiting for CAPTCHA solution for session {session_id}")
                captcha_solution = wait_for_captcha_solution(session_id)
                
                if captcha_solution:
                    # Fill CAPTCHA solution
                    captcha_input.clear()
                    captcha_input.send_keys(captcha_solution)
                    print(f"CAPTCHA solution entered: {captcha_solution}")
                else:
                    raise Exception("CAPTCHA solution timeout - user did not respond in time")
            else:
                raise Exception("Could not capture CAPTCHA image")
        
        except Exception as e:
            raise Exception(f"CAPTCHA handling failed: {e}")
        
        session_manager.update_session(session_id, status='submitting_form', progress=50)
        
        # Submit form
        search_button = driver.find_element(By.XPATH, "//button[@id='govAgenciesSearch']")
        driver.execute_script("arguments[0].click();", search_button)
        time.sleep(5)
        
        session_manager.update_session(session_id, status='extracting_data', progress=70)
        
        # Extract results (same as your existing code)
        table_data = extract_table_data(driver)
        
        # Continue with product extraction if needed
        session_manager.update_session(session_id, status='extracting_products', progress=90)
        
        final_result = {
            'extraction_timestamp': datetime.now().isoformat(),
            'license_number': license_number,
            'search_results': table_data,
            'summary': {
                'total_records': len(table_data),
                'search_successful': len(table_data) > 0
            }
        }
        
        session_manager.update_session(
            session_id,
            status='completed',
            progress=100,
            result=final_result
        )
        
        return final_result
        
    except Exception as e:
        session_manager.update_session(
            session_id,
            status='error',
            error=str(e),
            progress=100
        )
        raise e
    
    finally:
        # Clean up browser
        if session_id in session_manager.sessions:
            driver = session_manager.sessions[session_id].get('driver')
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                session_manager.sessions[session_id]['driver'] = None

