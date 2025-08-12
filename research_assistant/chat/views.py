from flask import Blueprint, jsonify, request

chat_bp = Blueprint('chat', __name__, url_prefix='/api')

@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    对应前端 fetchChatReply() 调用的 /api/chat
    """
    data = request.get_json() or {}
    user_input = data.get('message', '')
    # TODO: Call the real LLM interface here; currently, it is mocked
    reply = f"[模拟回答] 收到消息：{user_input}"
    return jsonify({'reply': reply}), 200
