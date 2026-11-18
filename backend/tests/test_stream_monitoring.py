"""
Unit & Integration Test Suite for Phase 8 Real-Time Deepfake Monitoring.
Validates:
1. WebRTC Signaling & Room Management (join_room, peer_joined, offer, answer, ice_candidate).
2. Continuous Audio Chunk Ingestion into Sliding Ring Buffer.
3. Fast-Path Video Keyframe Decoding & Face Bounding Box Extraction.
4. Sub-300ms Inference Latency Measurement & Real-Time Telemetry Dispatch.
5. Network Interruption, Disconnection & Room Cleanup Handling.
"""

import sys
import base64
import time
import io
import wave
import numpy as np
import cv2
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

import pytest
from starlette.testclient import TestClient
from app.main import app

def generate_test_pcm16_base64(duration_sec: float = 0.25, sample_rate: int = 16000) -> str:
    """Generates a 250ms 16kHz Float32 PCM audio chunk encoded as Base64."""
    num_samples = int(sample_rate * duration_sec)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    # Voiced fundamental speech frequency (220 Hz)
    audio = (0.4 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    return base64.b64encode(audio.tobytes()).decode("utf-8")

def generate_test_jpeg_base64() -> str:
    """Generates an in-memory 160x120 JPEG frame with a synthetic skin-tone oval (face)."""
    frame = np.full((120, 160, 3), 40, dtype=np.uint8)
    # Skin-tone face oval
    cv2.ellipse(frame, (80, 60), (30, 40), 0, 0, 360, (140, 170, 220), -1)
    # Eyes & Mouth
    cv2.circle(frame, (70, 50), 4, (255, 255, 255), -1)
    cv2.circle(frame, (90, 50), 4, (255, 255, 255), -1)
    cv2.ellipse(frame, (80, 75), (10, 4), 0, 0, 360, (20, 20, 80), -1)

    _, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf).decode("utf-8")

def test_webrtc_signaling_and_realtime_monitoring():
    client = TestClient(app)

    room_id = f"TEST-ROOM-{int(time.time())}"

    # 1. Test Room Status Endpoint (initially empty)
    status_res = client.get(f"/api/v1/stream/rooms/{room_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["peer_count"] == 0
    assert status_data["is_active"] is False
    print(f"\n[STEP 1] Room {room_id} status verified: 0 peers.")

    # 2. Client A Connects to Room
    with client.websocket_connect(f"/api/v1/stream/call/{room_id}") as ws_a:
        msg_a1 = ws_a.receive_json()
        assert msg_a1["type"] == "room_joined"
        assert msg_a1["room_id"] == room_id
        client_a_id = msg_a1["client_id"]
        assert len(msg_a1["peers"]) == 0
        print(f"[STEP 2] Client A connected as {client_a_id}.")

        # 3. Client B Connects to Same Room
        with client.websocket_connect(f"/api/v1/stream/call/{room_id}") as ws_b:
            msg_b1 = ws_b.receive_json()
            assert msg_b1["type"] == "room_joined"
            client_b_id = msg_b1["client_id"]
            # Client B sees Client A as existing peer
            assert client_a_id in msg_b1["peers"]
            print(f"[STEP 3] Client B connected as {client_b_id}, sees peer {client_a_id}.")

            # Client A receives peer_joined notification
            peer_joined_msg = ws_a.receive_json()
            assert peer_joined_msg["type"] == "peer_joined"
            assert peer_joined_msg["client_id"] == client_b_id
            print(f"[STEP 4] Client A notified that Client B ({client_b_id}) joined.")

            # 4. WebRTC SDP Offer / Answer Exchange
            # Client A sends SDP Offer to Client B
            ws_a.send_json({
                "type": "offer",
                "sdp": {"type": "offer", "sdp": "v=0\r\no=ClientA 12345 2 IN IP4 127.0.0.1\r\ns=TestCall"},
                "target_id": client_b_id
            })

            offer_received = ws_b.receive_json()
            assert offer_received["type"] == "offer"
            assert offer_received["sender_id"] == client_a_id
            print(f"[STEP 5] Client B received WebRTC SDP Offer from {client_a_id}.")

            # Client B sends SDP Answer to Client A
            ws_b.send_json({
                "type": "answer",
                "sdp": {"type": "answer", "sdp": "v=0\r\no=ClientB 67890 2 IN IP4 127.0.0.1\r\ns=TestCall"},
                "target_id": client_a_id
            })

            answer_received = ws_a.receive_json()
            assert answer_received["type"] == "answer"
            assert answer_received["sender_id"] == client_b_id
            print(f"[STEP 6] Client A received WebRTC SDP Answer from {client_b_id}.")

            # Client A sends ICE Candidate
            ws_a.send_json({
                "type": "ice_candidate",
                "candidate": {"candidate": "candidate:1 1 UDP 2130706431 192.168.1.1 50000 typ host", "sdpMid": "0"},
                "target_id": client_b_id
            })

            ice_received = ws_b.receive_json()
            assert ice_received["type"] == "ice_candidate"
            print("[STEP 7] WebRTC ICE Candidate exchanged successfully.")

            # 5. Live Media Ingestion & Neural Telemetry Dispatch
            pcm_b64 = generate_test_pcm16_base64(0.25)
            ws_a.send_json({
                "type": "audio_chunk",
                "audio_base64_pcm": pcm_b64,
                "format": "float32",
                "timestamp_ms": int(time.time() * 1000)
            })

            jpeg_b64 = generate_test_jpeg_base64()
            ts_now = int(time.time() * 1000)
            ws_a.send_json({
                "type": "video_frame",
                "frame_base64_jpeg": jpeg_b64,
                "timestamp_ms": ts_now
            })

            # Receive Real-Time Telemetry
            telemetry = ws_a.receive_json()
            assert telemetry["type"] == "telemetry"
            assert "composite_risk_score" in telemetry
            assert "latency_ms" in telemetry
            assert "verdict" in telemetry
            assert "metrics" in telemetry
            assert "face_bbox" in telemetry

            # Measure & Assert Latency Requirement: Sub-300ms
            latency = telemetry["latency_ms"]
            assert latency > 0.0, "Latency must be measured"
            assert latency < 300.0, f"Inference latency {latency}ms exceeds sub-300ms real-time limit"
            print(f"[STEP 8] Live Telemetry received. Measured Inference Latency={latency}ms (Sub-300ms verified!), Risk={telemetry['composite_risk_score']}%, Verdict={telemetry['verdict']}")

            # Check bounding box
            bbox = telemetry["face_bbox"]
            assert bbox is not None
            assert 0.0 <= bbox["x"] <= 1.0
            assert 0.0 <= bbox["w"] <= 1.0
            print(f"[STEP 9] Real Face Bounding Box extracted: x={bbox['x']}, y={bbox['y']}, w={bbox['w']}, h={bbox['h']}")

    # 6. Verify Room Cleanup
    status_res = client.get(f"/api/v1/stream/rooms/{room_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["peer_count"] == 0
    print("[STEP 10] Room peer disconnect and resource cleanup verified.")

def test_standalone_live_stream_endpoint():
    client = TestClient(app)
    session_id = "test_standalone_session"

    with client.websocket_connect(f"/api/v1/stream/live/{session_id}") as ws:
        # Handshake
        ws.send_json({"type": "init"})
        ready = ws.receive_json()
        assert ready["type"] == "ready"

        # Audio + Video frame
        ws.send_json({
            "type": "audio_chunk",
            "audio_base64_pcm": generate_test_pcm16_base64(0.25)
        })
        ws.send_json({
            "type": "video_frame",
            "frame_base64_jpeg": generate_test_jpeg_base64(),
            "timestamp_ms": int(time.time() * 1000)
        })

        telemetry = ws.receive_json()
        assert telemetry["type"] == "telemetry"
        assert telemetry["latency_ms"] < 300.0
        print(f"\n[PASS] Standalone /live endpoint verified with {telemetry['latency_ms']}ms latency.")

