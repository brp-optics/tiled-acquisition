import time
import pathlib
import zulip
import threading
import signal
import sys
from datetime import datetime, timedelta

# Configuration
total_images = 1870
time_per_image = 90  # sec
sleep_time = time_per_image * 1.5  # sec
folder = r'D:\UserData\HelenWilson\20250417_bigfovMN_slim\MN_nras_1tissue_0417'
zuliprc_path = "C:/Users/lociuser/Documents/zuliprc"
stream_name = "SLIM-acquisition-messages"
topic_name = "Acquisition status"

# Global variables for status tracking
current_files = 0
percent_complete = 0.0
monitoring_active = False
last_check_time = None

# Control flag for threads
running = True

# Create a Zulip client
client = zulip.Client(config_file=zuliprc_path)

def get_number_of_files(folder=folder):
    return len(list(pathlib.Path(folder).glob('*.sdt')))

def send_zulip_message(message, topic=topic_name):
    request = {
        "type": "stream",
        "to": stream_name,
        "topic": topic,
        "content": message,
    }
    result = client.send_message(request)
    print(f"Message sent: {message}")
    return result

def check_for_status_messages():
    """Poll for messages asking for status."""
    global current_files, percent_complete, last_check_time, monitoring_active
    
    # Calculate a timestamp for 5 minutes ago (increase time window)
    now = datetime.now()
    five_min_ago = now - timedelta(minutes=5)
    # Format as required by Zulip API
    anchor_timestamp = five_min_ago.strftime('%Y-%m-%d %H:%M:%S')
    
    # Get recent messages
    request = {
        "anchor": "newest",  # Changed from timestamp to "newest" to get most recent messages
        "num_before": 20,    # Check more messages to increase chances of finding status requests
        "num_after": 0,      # We don't need messages after the anchor
        
    }
    
    try:
        result = client.get_messages(request)
        
        if result["result"] == "success":
            messages = result["messages"]
            print(f"Found {len(messages)} messages in the stream")
            
            # Process messages from newest to oldest
            for msg in messages:
                # Print content for debugging
                print(f"Message content: '{msg.get('content', '')}'")
                
                # Convert timestamp to datetime for comparison
                msg_time = datetime.fromtimestamp(msg["timestamp"])
                
                # Only process messages from the last 5 minutes
                if now - msg_time > timedelta(minutes=5):
                    print(f"Message from {msg_time} too old, skipping")
                    continue
                
                # More lenient check for status-related terms
                content = msg.get('content', '').lower()
                if "status" in content or "progress" in content or "update" in content:
                    print(f"Found status request: {msg['content']}")
                    
                    # Send status response
                    status_message = (
                        f"Current status: {current_files}/{total_images} files processed "
                        f"({percent_complete:.2f}% complete)\n"
                    )
                    
                    if monitoring_active:
                        if last_check_time:
                            time_since_check = time.time() - last_check_time
                            status_message += f"Last check: {time_since_check:.1f} seconds ago"
                        else:
                            status_message += "Monitoring is active but no checks completed yet"
                    else:
                        status_message += "Monitoring is currently inactive"
                    
                    # Use the topic of the incoming message
                    incoming_topic = msg.get("topic",topic_name)
                    send_zulip_message(status_message, topic=incoming_topic)
                    print("Status response sent!")
                    
                    # Only respond to one status request per polling cycle
                    break
    except Exception as e:
        print(f"Error checking messages: {e}")
        # Print the full exception for debugging
        import traceback
        traceback.print_exc()

def message_polling_thread():
    """Thread function that polls for status requests."""
    global running
    
    print("Message polling thread started")
    while running:
        try:
            #print("Checking for status messages...")
            check_for_status_messages()
        except Exception as e:
            print(f"Error in message polling: {e}")
        
        # Poll every 5 seconds (reduced from 10) for better responsiveness
        for _ in range(5):
            if not running:
                break
            time.sleep(1)
            
    print("Message polling thread stopped")

def file_monitoring_thread():
    """Thread function that monitors the files."""
    global current_files, percent_complete, monitoring_active, last_check_time, running
    
    print("File monitoring thread started")
    monitoring_active = True
    send_zulip_message(f"Starting monitoring of {folder}")
    
    try:
        current_files = get_number_of_files()
        percent_complete = current_files * 100.0 / total_images
        
        for i in range(90 * total_images):
            if not running:
                break
                
            nfiles = current_files
            last_check_time = time.time()
            
            # Sleep with periodic checks for stop signal
            sleep_start = time.time()
            while running and (time.time() - sleep_start) < sleep_time:
                time.sleep(1)
                
            if not running:
                break
                
            current_files = get_number_of_files()
            percent_complete = current_files * 100.0 / total_images
            
            print(f"Files: {nfiles} → {current_files} ({percent_complete:.2f}%)")
            
            if current_files > nfiles:
                # New files detected, continue silently
                pass
            else:
                # No new files, send alert
                message = f"NO NEW FILES at {current_files} completed ({percent_complete:.2f}%)"
                send_zulip_message(message)
            
            # Check if acquisition is complete
            if current_files >= total_images:
                break
                
        if running:  # Only send completion message if not interrupted
            message = f"Monitoring complete. Final count: {current_files}/{total_images} files ({percent_complete:.2f}%)"
            send_zulip_message(message)
    
    finally:
        monitoring_active = False
        print("File monitoring thread stopped")

def signal_handler(sig, frame):
    """Handle Ctrl+C and other termination signals."""
    global running
    print("\nShutting down gracefully... (This might take a few seconds)")
    running = False

def main():
    """Main function to start both threads."""
    global running
    
    # Set up signal handler for graceful exit
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the message polling thread
    polling_thread = threading.Thread(target=message_polling_thread)
    polling_thread.start()
    
    # Start the file monitoring thread
    monitor_thread = threading.Thread(target=file_monitoring_thread)
    monitor_thread.start()
    
    # Wait for threads to complete or until interrupted
    try:
        while running and (polling_thread.is_alive() or monitor_thread.is_alive()):
            time.sleep(0.5)
    except Exception as e:
        print(f"Error in main thread: {e}")
        running = False
    
    # Wait for threads to finish
    if polling_thread.is_alive():
        polling_thread.join(timeout=5)
    if monitor_thread.is_alive():
        monitor_thread.join(timeout=5)
        
    print("Script terminated")
    
    # Force exit in case threads are still hanging
    sys.exit(0)

if __name__ == "__main__":
    main()