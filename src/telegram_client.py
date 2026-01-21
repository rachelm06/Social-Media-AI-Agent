"""
Telegram Client for Human-in-the-Loop (HITL) approval workflow.
"""
import os
import asyncio
from typing import Optional, Tuple
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram import Update
from telegram.error import BadRequest


class TelegramClient:
    """Client for Telegram HITL approval workflow."""
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram client.
        
        Args:
            bot_token: Telegram bot token. If None, will try to get from environment.
            chat_id: Telegram chat ID. If None, will try to get from environment.
        """
        self.bot_token = (bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
        self.chat_id = (chat_id or os.getenv("TELEGRAM_CHAT_ID", "")).strip()
        
        if not self.bot_token:
            raise ValueError("Telegram bot token is required. Set TELEGRAM_BOT_TOKEN in .env file.")
        if not self.chat_id:
            raise ValueError("Telegram chat ID is required. Set TELEGRAM_CHAT_ID in .env file.")
        
        self.chat_id_int = int(self.chat_id)
    
    async def wait_for_approval(
        self, 
        post_content: str,
        image_url: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Send post for approval and wait for human decision.
        If rejected, collect feedback reason.
        
        Args:
            post_content: The post text content to approve
            image_url: Optional URL of image attached to the post
            
        Returns:
            Tuple of (decision, rejection_reason)
            - decision: "approve" or "reject"
            - rejection_reason: None if approved, feedback text if rejected
        """
        # Global state for the approval flow
        pending_post = post_content
        decision_result = None
        feedback_reason = None
        waiting_for_reason = False
        feedback_done = asyncio.Event()
        
        async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle approve/reject button clicks."""
            nonlocal decision_result, waiting_for_reason
            
            query = update.callback_query
            try:
                await query.answer()
            except BadRequest as e:
                if "Query is too old" not in str(e) and "query_id invalid" not in str(e):
                    raise
            
            if query.data == "approve":
                decision_result = "approve"
                message_text = f"✅ APPROVED\n\n{pending_post}"
                if image_url:
                    message_text += f"\n\n🖼️ Image: {image_url}"
                try:
                    await query.edit_message_text(message_text)
                except BadRequest:
                    pass  # Message might already be edited
                feedback_done.set()
            elif query.data == "reject":
                decision_result = "reject"
                waiting_for_reason = True
                try:
                    await query.edit_message_text(
                        "❌ REJECTED\n\n"
                        "Please reply with the reason for rejection.\n"
                        "This feedback helps improve future posts.\n\n"
                        "Examples: 'Too promotional' or 'Wrong tone'"
                    )
                except BadRequest:
                    pass
        
        async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Handle text feedback when post is rejected."""
            nonlocal feedback_reason, waiting_for_reason
            
            if not waiting_for_reason:
                return
            
            feedback_reason = update.message.text
            waiting_for_reason = False
            await update.message.reply_text(
                f"📝 Feedback recorded!\n\nReason: {feedback_reason}"
            )
            feedback_done.set()
        
        # Reset state
        decision_result = None
        feedback_reason = None
        waiting_for_reason = False
        feedback_done.clear()
        
        # Build the message text
        message_text = f"📝 New Post for Approval\n\n{pending_post}\n\nCharacters: {len(post_content)}"
        if image_url:
            message_text += f"\n\n🖼️ Image will be attached: {image_url}"
        
        # Send the post with buttons
        bot = Bot(token=self.bot_token)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data="approve"),
                InlineKeyboardButton("❌ Reject", callback_data="reject"),
            ]
        ])
        
        await bot.send_message(
            chat_id=self.chat_id_int,
            text=message_text,
            reply_markup=keyboard,
        )
        print("📱 Sent to Telegram. Waiting for approval...")
        
        # Set up the application and listeners
        app = Application.builder().token(self.bot_token).build()
        app.add_handler(CallbackQueryHandler(handle_button))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Wait for decision
        try:
            await asyncio.wait_for(feedback_done.wait(), timeout=300)  # 5 minute timeout
        except asyncio.TimeoutError:
            print("⏱️ Approval timeout after 5 minutes. Defaulting to reject.")
            decision_result = "reject"
            feedback_reason = "Timeout - no response received"
        
        # Cleanup
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        
        return decision_result, feedback_reason
    
    def request_approval_sync(
        self,
        post_content: str,
        image_url: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Synchronous wrapper for wait_for_approval.
        
        Args:
            post_content: The post text content to approve
            image_url: Optional URL of image attached to the post
            
        Returns:
            Tuple of (decision, rejection_reason)
        """
        # Check if there's already an event loop running
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we need to run in a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.wait_for_approval(post_content, image_url)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.wait_for_approval(post_content, image_url)
                )
        except RuntimeError:
            # No event loop, create a new one
            return asyncio.run(self.wait_for_approval(post_content, image_url))
