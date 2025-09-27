# import time


# def extract_license_with_llm(url: str, max_retries: int = 2) -> dict:
#     combined_text = scrape_text_and_images(url)
#     prompt = (
#         "Extract the following fields from the given scraped website content. "
#         "Return ONLY a valid JSON object (no explanation, no text outside JSON). "
#         "If data is missing, use null or empty string. "
#         "Fields:\n"
#         "- license_number (manufacturer Lic. No. / FSSAI Lic. No.)\n"
#         "- shelf_life (e.g. 'Best before 12 months from MFG')\n"
#         "- expiry_date (if mentioned)\n"
#         "- manufacturer_name (if available)\n"
#         "\nText:\n" +
#         combined_text
#     )
#     for attempt in range(max_retries):
#         response = model.generate_content(prompt)
#         response_text = response.text.strip()
#         json_start = response_text.find('{')
#         json_end = response_text.rfind('}') + 1
#         if json_start >= 0 and json_end > 0:
#             json_str = response_text[json_start:json_end]
#             try:
#                 data = json.loads(json_str)
#                 return data
#             except json.JSONDecodeError as e:
#                 logging.error(f"JSON parsing error: {e}")
#         else:
#             logging.warning("No JSON object found from Gemini response.")
#     return {"error": "Failed to get valid JSON from Gemini", "raw_response": response_text}


# def automate_foscos_form(license_number: str):
#     options = webdriver.ChromeOptions()
#     options.add_argument("--start-maximized")
#     # options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--window-size=1920,1080")
#     options.add_argument("--disable-blink-features=AutomationControlled")
#     options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     options.add_experimental_option('useAutomationExtension', False)

#     options.add_argument("--disable-web-security")
#     options.add_argument("--disable-features=VizDisplayCompositor")
#     options.add_argument("--remote-debugging-port=9222")
#     options.add_argument("--disable-background-timer-throttling")
#     options.add_argument("--disable-backgrounding-occluded-windows")
#     options.add_argument("--disable-renderer-backgrounding")
#     options.add_argument("--ignore-certificate-errors")
#     options.add_argument("--ignore-ssl-errors")
#     options.add_argument("--ignore-certificate-errors-spki-list")

#     # options.binary_location = "/usr/bin/chromium-browser"
#     if os.name == 'nt':  # Windows
#         # Remove the Linux-specific binary location
#         # options.binary_location will use system default Chrome
#         pass
#     else:  # Linux/Unix
#         options.binary_location = "/usr/bin/chromium-browser"
    
#     driver = webdriver.Chrome(options=options)
#     captcha_solver = CaptchaSolver(CAPTCHA_API_KEY)
#     wait = WebDriverWait(driver, 9)
    
#     # Initialize result structure
#     foscos_data = {
#         "license_search_results": [],
#         "product_details": None,
#         "search_successful": False,
#         "products_extracted": False
#     }

#     try:
#         # Navigate to the main FoSCoS website
#         driver.get("https://foscos.fssai.gov.in")
        
#         print("Navigating to FoSCoS website...")
#         time.sleep(3)  # Allow page to load completely
        
#         # Click on "FBO Search" tab in the navigation menu
#         print("Looking for FBO Search tab...")
#         fbo_search_tab = None
        
#         # Try to find the specific FBO Search tab with exact attributes
#         fbo_search_selectors = [
#             "//a[@id='governmentAgencies1']",
#             "//a[@href='#governmentAgenciesDiv1']",
#             "//a[contains(@id, 'governmentAgencies1') and contains(text(), 'FBO Search')]",
#             "//a[@data-toggle='tab' and @href='#governmentAgenciesDiv1']",
#             "//a[contains(@href, 'governmentAgenciesDiv1')]",
#             "//a[.//b[text()='FBO Search']]",
#             "//b[text()='FBO Search']/parent::a"
#         ]
        
#         for selector in fbo_search_selectors:
#             try:
#                 fbo_search_tab = driver.find_element(By.XPATH, selector)
#                 if fbo_search_tab.is_displayed() and fbo_search_tab.is_enabled():
#                     print(f"Found FBO Search tab with selector: {selector}")
#                     break
#             except:
#                 continue
        
#         if fbo_search_tab:
#             # Click the FBO Search tab to open the form
#             driver.execute_script("arguments[0].click();", fbo_search_tab)
#             print("Clicked on FBO Search tab")
#             time.sleep(3)
#         else:
#             print("FBO Search tab not found. Proceeding to look for form directly...")
        
#         # Look for the License/Registration Certificate No. input field
#         print("Looking for license input field...")
#         license_input = None
        
#         # Based on your image, the placeholder text is "License/Registration No."
#         license_input_selectors = [
#             "//input[@placeholder='License/Registration No.']",
#             "//input[contains(@placeholder, 'License/Registration')]",
#             "//input[contains(@placeholder, 'License')]",
#             "//input[@name='licenseNo']",
#             "//input[@id='licenseNo']",
#             "(//input[@type='text'])[2]",  # Second text input based on form structure
#             "//input[contains(@class, 'form-control')]"
#         ]
        
#         for selector in license_input_selectors:
#             try:
#                 license_input = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
#                 print(f"Found license input field with selector: {selector}")
#                 break
#             except:
#                 continue
        
#         if license_input:
#             # Clear and enter the license number
#             license_input.clear()
#             time.sleep(1)
#             license_input.send_keys(license_number)
#             print(f"✓ Entered license number: {license_number}")
            
#             # Scroll to the license input to ensure it's visible
#             driver.execute_script("arguments[0].scrollIntoView(true);", license_input)
#             time.sleep(1)
#         else:
#             print("❌ License input field not found!")
#             return foscos_data
        
#         # Find CAPTCHA elements
#         print("Looking for CAPTCHA image...")
#         captcha_image = None
#         captcha_input = None
        
#         # Find CAPTCHA image
#         captcha_image_selectors = [
#             "//img[@alt='Captcha']",
#             "//img[contains(@src, 'data:image')]",
#             "//img[contains(@alt, 'captcha')]",
#             "//img[contains(@alt, 'Captcha')]"
#         ]
        
#         for selector in captcha_image_selectors:
#             try:
#                 captcha_image = driver.find_element(By.XPATH, selector)
#                 if captcha_image.is_displayed():
#                     print(f"Found CAPTCHA image with selector: {selector}")
#                     break
#             except:
#                 continue
        
#         # Find CAPTCHA input field
#         captcha_input_selectors = [
#             "//input[@placeholder='Enter Captcha Code']",
#             "//input[@formcontrolname='captcha']",
#             "//input[@id='govAgenciesSearch'][@type='text']",
#             "//input[contains(@placeholder, 'Captcha')]"
#         ]
        
#         for selector in captcha_input_selectors:
#             try:
#                 captcha_input = driver.find_element(By.XPATH, selector)
#                 if captcha_input.is_displayed():
#                     print(f"Found CAPTCHA input field with selector: {selector}")
#                     break
#             except:
#                 continue
        
#         captcha_solved = False
        
#         if captcha_image and captcha_input:
#             # First try automatic CAPTCHA solving
#             print("🔄 Attempting automatic CAPTCHA solving...")
            
#             # Get image data
#             image_base64 = captcha_solver.get_image_base64_from_element(driver, captcha_image)
            
#             if image_base64:
#                 # Solve CAPTCHA
#                 captcha_solution = captcha_solver.solve_image_captcha(image_base64)
                
#                 if captcha_solution:
#                     # Enter CAPTCHA solution
#                     captcha_input.clear()
#                     time.sleep(1)
#                     captcha_input.send_keys(captcha_solution)
#                     print(f"✅ CAPTCHA solution entered automatically: {captcha_solution}")
#                     captcha_solved = True
#                     time.sleep(1)
#                 else:
#                     print("❌ Automatic CAPTCHA solving failed")
            
#             # If automatic solving failed, wait for manual input
#             if not captcha_solved:
#                 print("\n" + "="*60)
#                 print("🔧 AUTOMATIC CAPTCHA SOLVING FAILED")
#                 print("👤 PLEASE SOLVE THE CAPTCHA MANUALLY")
#                 print("="*60)
                
#                 # Wait for user to manually fill CAPTCHA
#                 captcha_filled = wait_for_manual_captcha(driver, captcha_input, max_wait_time=20)
                
#                 if captcha_filled:
#                     print("✅ Manual CAPTCHA entry detected!")
#                     captcha_solved = True
#                     # Wait 3 seconds after user fills CAPTCHA
#                     print("⏰ Waiting 3 seconds before submitting...")
#                     time.sleep(3)
#                 else:
#                     # If no manual input, still try to submit
#                     print("⚠️ No manual CAPTCHA input detected, proceeding anyway...")
#         else:
#             print("❌ CAPTCHA elements not found!")
        
#         # Look for search/submit button
#         print("Looking for search button...")
#         search_button = None
        
#         search_button_selectors = [
#             "//button[@id='govAgenciesSearch'][@type='button']",
#             "//button[contains(text(), 'Search')]",
#             "//button[contains(@class, 'btn-default') and contains(text(), 'Search')]",
#             "//input[@type='submit']", 
#             "//button[@type='submit']",
#             "//input[@value='Search']",
#             "//button[contains(@class, 'btn') and contains(text(), 'Search')]"
#         ]
        
#         for selector in search_button_selectors:
#             try:
#                 search_button = driver.find_element(By.XPATH, selector)
#                 if search_button.is_displayed() and search_button.is_enabled():
#                     print(f"Found search button with selector: {selector}")
#                     break
#             except:
#                 continue
        
#         if search_button:
#             # Scroll to button and click
#             driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
#             time.sleep(2)
#             driver.execute_script("arguments[0].click();", search_button)
#             print("✅ Clicked search button")
#             time.sleep(1)
#         else:
#             print("❌ Search button not found!")
#             print("Please click the search button manually.")
#             time.sleep(3)
        
#         # Extract table data first
#         print("📊 Extracting search results table data...")
#         table_data = extract_table_data(driver)
#         foscos_data["license_search_results"] = table_data
#         foscos_data["search_successful"] = len(table_data) > 0
        
#         if table_data:
#             print(f"✅ Found {len(table_data)} license records in search results")
#             for record in table_data:
#                 print(f"  - {record['company_name']} | {record['license_number']} | {record['status']}")
#         else:
#             print("❌ No license data found in search results")
        
#         # Wait for results and look for "View Products" button
#         print("Looking for 'View Products' button...")
        
#         view_products_button = None
#         view_products_selectors = [
#             "//a[contains(text(), 'View Products')]",
#             "//a[contains(@style, 'cursor: pointer') and contains(@style, 'color: blue')]",
#             "//a[@_ngcontent-c4=''][contains(@style, 'cursor: pointer')]",
#             "//a[contains(@style, 'color: blue')]",
#             "//*[contains(text(), 'View Products')]"
#         ]
        
#         # Wait up to 15 seconds for View Products button (reduced time since we already have table data)
#         max_wait = 15
#         found_button = False
        
#         for i in range(max_wait):
#             for selector in view_products_selectors:
#                 try:
#                     view_products_button = driver.find_element(By.XPATH, selector)
#                     if view_products_button.is_displayed():
#                         print(f"✅ Found 'View Products' button with selector: {selector}")
#                         found_button = True
#                         break
#                 except:
#                     continue
            
#             if found_button:
#                 break
                
#             print(f"⏰ Looking for 'View Products' button... ({i+1}/{max_wait})")
#             time.sleep(1)
        
#         if view_products_button and found_button:
#             print("🔄 Clicking 'View Products' button...")
            
#             # Scroll to button and click
#             driver.execute_script("arguments[0].scrollIntoView(true);", view_products_button)
#             time.sleep(1)
#             driver.execute_script("arguments[0].click();", view_products_button)
#             print("✅ Clicked 'View Products' button")
            
#             # Wait for product details page to load
#             time.sleep(1)
            
#             # Extract all page content
#             print("📊 Extracting product details...")
#             page_content = driver.page_source
            
#             # Use LLM to extract structured data
#             extracted_data = extract_product_details_with_llm(page_content)
#             foscos_data["product_details"] = extracted_data
#             foscos_data["products_extracted"] = True
            
#             print("✅ Product details extracted successfully!")
            
#         else:
#             print("❌ 'View Products' button not found!")
#             print("Will return search results data only")
            
#             # Take screenshot for debugging
#             try:
#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 screenshot_path = f"debug_screenshot_{timestamp}.png"
#                 driver.save_screenshot(screenshot_path)
#                 print(f"📸 Screenshot saved: {screenshot_path}")
#             except:
#                 print("Could not save screenshot")
        
#         # Create final data structure
#         final_data = {
#             "extraction_timestamp": datetime.now().isoformat(),
#             "source_license_number": license_number,
#             "search_results": foscos_data["license_search_results"],
#             "product_details": foscos_data["product_details"],
#             "summary": {
#                 "search_successful": foscos_data["search_successful"],
#                 "products_extracted": foscos_data["products_extracted"],
#                 "total_records_found": len(foscos_data["license_search_results"])
#             },
#             "page_url": driver.current_url
#         }
        
#         # Save results to file
#         # save_results_to_file(final_data)
        
#         print("\n" + "="*50)
#         print("✅ PROCESS COMPLETED")
#         print("="*50)
#         print(f"📊 Found {len(table_data)} license records")
#         print(f"🔍 Products extracted: {foscos_data['products_extracted']}")
#         print("Keeping browser open for 30 seconds for manual inspection...")
        
#         for i in range(30, 0, -5):
#             print(f"⏰ Browser will close in {i} seconds...")
#             time.sleep(3)
            
#         return final_data
        
#     except Exception as e:
#         print(f"❌ Error during automation: {e}")
#         print("Keeping browser open for debugging...")
#         time.sleep(5)
#         return foscos_data
        
#     finally:
#         try:
#             driver.quit()
#             print("Browser closed.")
#         except:
#             pass



# Flask==3.0.0
# flask-cors==4.0.0
# requests==2.31.0
# beautifulsoup4==4.12.2
# Pillow==10.1.0
# selenium==4.15.0
# google-generativeai==0.3.2
# python-dotenv==1.0.0
# pytesseract==0.3.10
# gunicorn==21.2.0