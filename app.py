from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    LocationMessageContent
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
import os
#Azure CLU
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
clu_endpoint = os.getenv("ENDPOINT")
clu_key = os.getenv("API_KEY")
project_name = os.getenv("PROJECT_NAME")
deployment_name = os.getenv("DEPLOYMENT_NAME")    

line_handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@line_handler.add(event=MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    address = event.message.address
    result = analyze_address(address)
    entities = result['prediction']['entities']

    messages = []
    if len(entities) == 2 and entities[0]['category'] == 'city' and entities[1]['category'] == 'town':
        city = result['prediction']['entities'][0]['text']
        town = result['prediction']['entities'][1]['text']
        messages.append(TextMessage(text=f"你傳送的位址資訊的城市:{city}"))
        messages.append(TextMessage(text=f"你傳送的位址資訊的鄉鎮:{town}"))
    else:
        messages.append(TextMessage(text="無法辨識你傳送的位址資訊"))

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages
            )
        )

def analyze_address(address):
    credential = AzureKeyCredential(clu_key)
    client = ConversationAnalysisClient(clu_endpoint, credential)
    with client:
        result = client.analyze_conversation(
            task={
                "kind": "Conversation",
                "analysisInput": {
                    "conversationItem": {
                        "participantId": "1",
                        "id": "1",
                        "modality": "text",
                        "language": "zh-hant",
                        "text": address
                    },
                    "isLoggingEnabled": False
                },
                "parameters": {
                    "projectName": project_name,
                    "deploymentName": deployment_name,
                    "verbose": True
                }
            }
        )
    return result['result']

if __name__ == "__main__":
    app.run()