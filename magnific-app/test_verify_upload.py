"""
Playwright E2E test for URL verify and file upload feedback.
"""
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://localhost:8000"
IMAGE_FILE = "/home/debian/magnific/image.png"
VIDEO_FILE = "/home/debian/magnific/video.mp4"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))

    print("=" * 60)
    print("1. Loading app...")
    page.goto(BASE_URL, timeout=15000)
    expect(page).to_have_title("Magnific API Studio")
    print("   PASS")

    print("\n2. Selecting Kling 2.6 Motion Control (Std)...")
    page.select_option("#category-select", "video")
    page.select_option("#model-select", "kling-v2-6-motion-control-std")
    page.wait_for_timeout(1000)
    expect(page.locator("#generate-form")).to_be_visible()
    print("   PASS")

    # Test URL verify
    print("\n3. Testing URL verify button...")
    image_toggle = page.locator(".url-file-toggle[data-field='image_url']")
    verify_btn = image_toggle.locator(".url-verify-btn")
    expect(verify_btn).to_be_visible()
    print("   Verify button visible: PASS")

    # Enter a test URL and verify
    url_input = image_toggle.locator(".url-input")
    url_input.fill("https://httpbin.org/status/200")
    verify_btn.click()
    page.wait_for_timeout(3000)

    result = image_toggle.locator(".url-verify-result")
    expect(result).to_have_class("url-verify-result success")
    result_text = result.text_content()
    print(f"   Verify result: {result_text}")
    print("   PASS")

    # Test file upload feedback
    print("\n4. Testing file upload feedback...")
    # Switch to file mode
    image_toggle.locator(".toggle-tab[data-mode='file']").click()
    page.wait_for_timeout(300)

    # Upload file
    file_input = image_toggle.locator("input[type='file']")
    file_input.set_input_files(IMAGE_FILE)
    page.wait_for_timeout(500)

    # Check feedback
    feedback = image_toggle.locator(".file-upload-feedback")
    expect(feedback.locator(".file-upload-success")).to_be_visible()
    file_name = feedback.locator(".file-name").text_content()
    file_size = feedback.locator(".file-size").text_content()
    print(f"   File name: {file_name}")
    print(f"   File size: {file_size}")
    print("   PASS")

    # Test video upload feedback
    print("\n5. Testing video upload feedback...")
    video_toggle = page.locator(".url-file-toggle[data-field='video_url']")
    video_toggle.locator(".toggle-tab[data-mode='file']").click()
    page.wait_for_timeout(300)

    video_input = video_toggle.locator("input[type='file']")
    video_input.set_input_files(VIDEO_FILE)
    page.wait_for_timeout(500)

    video_feedback = video_toggle.locator(".file-upload-feedback")
    expect(video_feedback.locator(".file-upload-success")).to_be_visible()
    video_name = video_feedback.locator(".file-name").text_content()
    video_size = video_feedback.locator(".file-size").text_content()
    print(f"   File name: {video_name}")
    print(f"   File size: {video_size}")
    print("   PASS")

    # Check for JS errors
    print("\n6. Checking for JS errors...")
    if errors:
        print(f"   FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"     - {e[:120]}")
    else:
        print("   PASS: No JS errors")

    print("\n" + "=" * 60)
    if not errors:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")

    browser.close()
