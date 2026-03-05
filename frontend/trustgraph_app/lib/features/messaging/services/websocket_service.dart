import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as ws_status;
import '../../../core/config/api_config.dart';
import '../../../data/providers/api_client.dart';

/// Event types from the WebSocket server
enum WsEventType {
  newMessage,
  typing,
  stopTyping,
  readReceipt,
  heartbeatAck,
  error,
  connected,
  disconnected,
}

/// A parsed WebSocket event
class WsEvent {
  final WsEventType type;
  final Map<String, dynamic> data;

  const WsEvent({required this.type, required this.data});
}

/// WebSocket service for real-time messaging
class WebSocketService {
  WebSocketChannel? _channel;
  final ApiClient _apiClient;

  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;

  bool _isConnected = false;
  bool _shouldReconnect = true;
  int _reconnectAttempts = 0;
  static const int _maxReconnectAttempts = 10;
  static const Duration _heartbeatInterval = Duration(seconds: 30);

  // Stream controller for broadcasting events
  final _eventController = StreamController<WsEvent>.broadcast();

  /// Stream of WebSocket events
  Stream<WsEvent> get events => _eventController.stream;

  /// Whether the WebSocket is currently connected
  bool get isConnected => _isConnected;

  WebSocketService(this._apiClient);

  /// Connect to WebSocket server
  Future<void> connect() async {
    if (_isConnected) return;

    try {
      final token = await _apiClient.getAccessToken();
      if (token == null || token.isEmpty) {
        debugPrint('[WS] No auth token available');
        return;
      }

      // Build WebSocket URL from API config
      final wsUrl = ApiConfig.messagingWsUrl;

      final uri = Uri.parse('$wsUrl/ws?token=$token');

      debugPrint('[WS] Connecting to $uri');

      _channel = WebSocketChannel.connect(uri);

      // Wait for the connection to be established
      await _channel!.ready;

      _isConnected = true;
      _reconnectAttempts = 0;

      _eventController.add(const WsEvent(
        type: WsEventType.connected,
        data: {},
      ));

      // Start heartbeat
      _startHeartbeat();

      // Listen for messages
      _channel!.stream.listen(
        _handleMessage,
        onError: _handleError,
        onDone: _handleDone,
        cancelOnError: false,
      );

      debugPrint('[WS] Connected successfully');
    } catch (e) {
      debugPrint('[WS] Connection failed: $e');
      _isConnected = false;
      _scheduleReconnect();
    }
  }

  /// Handle incoming WebSocket message
  void _handleMessage(dynamic rawMessage) {
    try {
      final data = jsonDecode(rawMessage as String) as Map<String, dynamic>;
      final action = data['action'] ?? data['type'] ?? data['event'] ?? '';

      WsEventType type;
      switch (action) {
        case 'new_message':
          type = WsEventType.newMessage;
          break;
        case 'typing':
          type = WsEventType.typing;
          break;
        case 'stop_typing':
          type = WsEventType.stopTyping;
          break;
        case 'read_receipt':
          type = WsEventType.readReceipt;
          break;
        case 'heartbeat_ack':
          type = WsEventType.heartbeatAck;
          break;
        case 'error':
          type = WsEventType.error;
          break;
        default:
          debugPrint('[WS] Unknown event type: $action');
          return;
      }

      _eventController.add(WsEvent(type: type, data: data));
    } catch (e) {
      debugPrint('[WS] Message parse error: $e');
    }
  }

  /// Handle WebSocket error
  void _handleError(dynamic error) {
    debugPrint('[WS] Error: $error');
    _isConnected = false;
    _eventController.add(WsEvent(
      type: WsEventType.error,
      data: {'message': error.toString()},
    ));
  }

  /// Handle WebSocket connection closed
  void _handleDone() {
    debugPrint('[WS] Connection closed');
    _isConnected = false;
    _stopHeartbeat();
    _eventController.add(const WsEvent(
      type: WsEventType.disconnected,
      data: {},
    ));

    if (_shouldReconnect) {
      _scheduleReconnect();
    }
  }

  /// Send a message via WebSocket
  void sendMessage({
    required String conversationId,
    required String encryptedPayload,
    String messageType = 'text',
    String? encryptedKey,
    Map<String, dynamic>? metadata,
  }) {
    _send({
      'action': 'send_message',
      'conversation_id': conversationId,
      'encrypted_payload': encryptedPayload,
      'message_type': messageType,
      if (encryptedKey != null) 'encrypted_key': encryptedKey,
      if (metadata != null) 'metadata': metadata,
    });
  }

  /// Send typing indicator
  void sendTyping(String conversationId) {
    _send({
      'action': 'typing',
      'conversation_id': conversationId,
    });
  }

  /// Send stop typing indicator
  void sendStopTyping(String conversationId) {
    _send({
      'action': 'stop_typing',
      'conversation_id': conversationId,
    });
  }

  /// Send read receipt
  void sendReadReceipt(String conversationId, String messageId) {
    _send({
      'action': 'read_receipt',
      'conversation_id': conversationId,
      'message_id': messageId,
    });
  }

  /// Send raw JSON payload
  void _send(Map<String, dynamic> payload) {
    if (!_isConnected || _channel == null) {
      debugPrint('[WS] Not connected, cannot send');
      return;
    }

    try {
      _channel!.sink.add(jsonEncode(payload));
    } catch (e) {
      debugPrint('[WS] Send error: $e');
    }
  }

  /// Start heartbeat timer
  void _startHeartbeat() {
    _stopHeartbeat();
    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (_) {
      _send({'action': 'heartbeat'});
    });
  }

  /// Stop heartbeat timer
  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  /// Schedule reconnection with exponential backoff
  void _scheduleReconnect() {
    _reconnectAttempts++;
    
    if (_reconnectAttempts > _maxReconnectAttempts) {
      debugPrint('[WS] Max reconnect attempts ($_maxReconnectAttempts) reached, giving up');
      return;
    }

    _reconnectTimer?.cancel();
    final delay = Duration(
      seconds: (1 << (_reconnectAttempts - 1)).clamp(1, 30),
    );

    debugPrint('[WS] Reconnecting in ${delay.inSeconds}s '
        '(attempt $_reconnectAttempts/$_maxReconnectAttempts)');

    _reconnectTimer = Timer(delay, () {
      connect();
    });
  }

  /// Disconnect from WebSocket
  Future<void> disconnect() async {
    _shouldReconnect = false;
    _stopHeartbeat();
    _reconnectTimer?.cancel();

    if (_channel != null) {
      await _channel!.sink.close(ws_status.normalClosure);
      _channel = null;
    }

    _isConnected = false;
    debugPrint('[WS] Disconnected');
  }

  /// Dispose all resources
  Future<void> dispose() async {
    await disconnect();
    await _eventController.close();
  }
}
