import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LLM_api Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const ChatPage(),
    );
  }
}

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final TextEditingController _controller = TextEditingController();
  final String backendBaseUrl = 'http://localhost:8000';

  String _response = '';
  bool _loading = false;

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _loading = true;
      _response = '';
    });

    try {
      final uri = Uri.parse('$backendBaseUrl/chat');
      final body = jsonEncode({
        'model': 'gpt-4o-mini',
        'messages': [
          {'role': 'user', 'content': text}
        ]
      });

      final resp = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: body,
      );

      if (resp.statusCode == 200) {
        final data = jsonDecode(resp.body) as Map<String, dynamic>;
        final choices = data['choices'] as List<dynamic>?;
        final first = choices != null && choices.isNotEmpty ? choices.first : null;
        final message = first != null ? first['message'] as Map<String, dynamic>? : null;
        final content = message != null ? message['content'] as String? : null;
        setState(() => _response = content ?? 'No content');
      } else {
        setState(() => _response = 'Error: ${resp.statusCode} ${resp.body}');
      }
    } catch (e) {
      setState(() => _response = 'Exception: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('LLM_api Demo')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: _controller,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                labelText: '输入你的问题',
              ),
              onSubmitted: (_) => _send(),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _loading ? null : _send,
                child: _loading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('发送'),
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: SingleChildScrollView(
                child: Text(_response),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
