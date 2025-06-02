import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from src.config import MONGO_URL, MONGO_DB_NAME
from src.services.external_meeting_service import join_external_meeting
import logging
from src.config import ADMIN_GMAIL_EMAIL, ADMIN_GMAIL_PASSWORD
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]
calendar_events_collection = db["calendarEvents"]

async def check_and_join_meetings():
    """
    Coroutine that checks calendar events every minute and joins meetings if needed.
    """
    while True:
        try:
            # Get current time
            now = datetime.utcnow()
            
            # Find events that:
            # 1. Are starting within the next minute
            # 2. Have autoJoin set to true
            # 3. Have a hangoutLink
            # 4. Haven't been joined yet
            query = {
                "start.dateTime": {
                    "$gte": now.isoformat() + 'Z',
                    "$lt": (now + timedelta(minutes=1)).isoformat() + 'Z'
                },
                "autoJoin": True,
                "hangoutLink": {"$exists": True, "$ne": None},
                "isJoined": {"$ne": True}  # Track if meeting has been joined
            }
            
            events = await calendar_events_collection.find(query).to_list(length=None)
            
            for event in events:
                try:
                    logger.info(f"Attempting to join meeting: {event['summary']}")
                    
                    # Extract meeting details
                    meeting_id = event.get("meetingId")
                    hangout_link = event.get("hangoutLink")
                    user_id = event.get("user_id")
                    
                    if not all([meeting_id, hangout_link, user_id]):
                        logger.warning(f"Missing required fields for meeting: {event['summary']}")
                        continue
                    
                    # Join the meeting using join_external_meeting
                    join_result = await join_external_meeting(
                         hangout_link,
                        ADMIN_GMAIL_EMAIL, 
                        ADMIN_GMAIL_PASSWORD, 
                        duration_in_minutes=10, 
                        userId=user_id,             
                        meetingId=meeting_id,
                        max_wait_time_in_minutes=2,
                        eventId=event["_id"] 
                                                              )
                    
                    if join_result:
                        # Update the event to mark it as joined and save container ID
                        update_data = {
                            "isJoined": True,
                            "joinedAt": datetime.utcnow().isoformat() + 'Z',
                            "updatedAt": datetime.utcnow()
                        }
                        
                        # Add container ID if it exists in the response
                        if isinstance(join_result, dict) and 'container_id' in join_result:
                            update_data['container_id'] = join_result['container_id']
                        
                        await calendar_events_collection.update_one(
                            {"_id": event["_id"]},
                            {"$set": update_data}
                        )
                        logger.info(f"Successfully joined meeting: {event['summary']}")
                    else:
                        logger.error(f"Failed to join meeting: {event['summary']}")
                
                except Exception as e:
                    logger.error(f"Error processing event {event.get('summary')}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in check_and_join_meetings: {str(e)}")
        
        # Wait for 1 minute before next check
        await asyncio.sleep(60)

async def start_meeting_scheduler():
    """
    Start the meeting scheduler in the background.
    """
    try:
        logger.info("Starting meeting scheduler...")
        await check_and_join_meetings()
    except Exception as e:
        logger.error(f"Error in meeting scheduler: {str(e)}")
        # Restart the scheduler if it fails
        await start_meeting_scheduler() 