import logging, sys
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler

import base64, jupyter_client
from io import BytesIO
from Listener import Listener

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
	global kernel_client
	li = Listener()
	reply = kernel_client.execute_interactive(update.message.text, timeout=5.0, 
										  allow_stdin=False, 
                                          output_hook=li.output_cb)
	if li.text:
		text = li.escape_ansi_text()                              
		await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
	if li.img_data:
		image = base64.b64decode(li.img_data)
		bio = BytesIO()
		bio.name = 'image.png'
		bio.write(image)
		bio.seek(0)
		await context.bot.send_photo(chat_id=update.message.chat_id, photo=bio)
                
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: bot2.py TOKEN')
        sys.exit(0)
    else:
        token = sys.argv[1]
	
    kernel_manager, kernel_client = jupyter_client.manager.start_new_kernel(kernel_name='python')

    application = ApplicationBuilder().token(token).build()
    
    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    
    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    
    application.run_polling()
