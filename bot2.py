import logging, sys
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler
from telegram.constants import ParseMode

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
    global kernel_clients
    global kernel_tgids
    global new_tgid
    tgid = update.message.from_user.id
    if not tgid in kernel_tgids:
      kernel_tgids[new_tgid] = tgid
      new_tgid += 1
      if new_tgid==NUMBER_OF_CLIENTS:
        new_tgid = 0
    kernel_client = kernel_clients[kernel_tgids.index(tgid)]

    li = Listener(kernel_name)
    reply = kernel_client.execute_interactive(update.message.text, timeout=5.0, 
                          allow_stdin=False, 
                          output_hook=li.output_cb)
    if li.text:
        text = li.escape_ansi_text()                              
        text = '```\n' + text + '\n```'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.MARKDOWN_V2)
    if li.img_data:
        image = base64.b64decode(li.img_data)
        bio = BytesIO()
        bio.name = 'image.png'
        bio.write(image)
        bio.seek(0)
        await context.bot.send_photo(chat_id=update.message.chat_id, photo=bio)
                
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: bot2.py octave|python|ir TOKEN')
        sys.exit(0)
    else:
        kernel_name = sys.argv[1]
        token = sys.argv[2]
    
    kernel_managers = []
    kernel_clients  = []
    NUMBER_OF_CLIENTS = 25
    kernel_tgids = [None]*NUMBER_OF_CLIENTS
    new_tgid = 0
    for _ in range(NUMBER_OF_CLIENTS):
      kernel_manager, kernel_client = jupyter_client.manager.start_new_kernel(kernel_name=kernel_name)
      kernel_managers.append(kernel_manager)
      kernel_clients.append(kernel_client)

    application = ApplicationBuilder().token(token).build()
    
    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    
    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    
    application.run_polling()
