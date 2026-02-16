from email.message import EmailMessage
import sys

def debug_headers():
    msg = EmailMessage()
    msg.set_content("Text body")
    msg.add_alternative("<html><img src='cid:myimage'></html>", subtype='html')
    
    payloads = msg.get_payload()
    html_part = payloads[0] # In this simple case, get_payload returns list? 
    # Wait, add_alternative makes it multipart/alternative.
    # [0] is text/plain, [1] is text/html usually? 
    # Let's check logic used in sender.py
    
    # Re-simulating sender.py logic
    msg = EmailMessage()
    msg.set_content("Text")
    msg.add_alternative("HTML", subtype='html')
    payloads = msg.get_payload()
    html_part = payloads[-1] # This is text/html
    
    # Embed image
    img_data = b"fakeimage"
    cid_param = "<myimage>"
    html_part.add_related(
        img_data, 
        maintype='image', 
        subtype='png', 
        cid=cid_param
    )
    
    # Now inspect the related part
    # html_part is now multipart/related
    related_payloads = html_part.get_payload()
    # [0] is text/html, [1] is image
    img_part = related_payloads[1]
    
    print("--- Headers for Image Part ---")
    for k, v in img_part.items():
        print(f"{k}: {v}")
        
    print("\n--- Testing Fix: Adding filename ---")
    # Try adding filename
    html_part = payloads[-1] # It's the same object reference? No, structure changed.
    # The 'html_part' variable held the text/html part, but add_related MUTATED it into multipart/related.
    # So html_part is now the multipart/related container.
    # We want to add another image to verify header changes.
    
    html_part.add_related(
        img_data,
        maintype='image',
        subtype='png',
        cid='<myimage3>',
        filename='image.png',
        disposition='inline'
    )
    img_part3 = html_part.get_payload()[-1]
    print("\n--- Headers for Image Part with Filename AND explicit inline ---")
    for k, v in img_part3.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    debug_headers()
