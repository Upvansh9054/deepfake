import json
import logging
import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from app.ml.stream_processor import StreamProcessor

router = APIRouter()
logger = logging.getLogger("deepfake_shield.stream")

class RoomSignalingManager:
    """
    Manages WebRTC peer connections, room dispatch, and per-session AI StreamProcessors.
    """
    def __init__(self):
        # room_id -> { client_id: WebSocket }
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}
        # client_id -> room_id
        self.client_room_map: Dict[str, str] = {}
        # client_id -> StreamProcessor
        self.processors: Dict[str, StreamProcessor] = {}

    async def connect_client(self, websocket: WebSocket, room_id: str, client_id: str) -> None:
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        self.rooms[room_id][client_id] = websocket
        self.client_room_map[client_id] = room_id
        self.processors[client_id] = StreamProcessor(session_id=client_id)
        logger.info(f"Client {client_id} joined room {room_id}. Current peers: {len(self.rooms[room_id])}")

    async def disconnect_client(self, client_id: str) -> None:
        room_id = self.client_room_map.pop(client_id, None)
        self.processors.pop(client_id, None)

        if room_id and room_id in self.rooms:
            self.rooms[room_id].pop(client_id, None)
            # Notify remaining peers in the room
            for peer_id, ws in list(self.rooms[room_id].items()):
                try:
                    await ws.send_json({
                        "type": "peer_left",
                        "client_id": client_id,
                        "room_id": room_id
                    })
                except Exception:
                    pass

            if len(self.rooms[room_id]) == 0:
                del self.rooms[room_id]
                logger.info(f"Room {room_id} closed as all peers disconnected.")

    async def broadcast_to_room(self, room_id: str, sender_id: str, message: dict) -> None:
        if room_id not in self.rooms:
            return
        for peer_id, ws in list(self.rooms[room_id].items()):
            if peer_id != sender_id:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to forward message to {peer_id}: {e}")

    async def send_to_peer(self, room_id: str, target_id: str, message: dict) -> bool:
        if room_id in self.rooms and target_id in self.rooms[room_id]:
            try:
                await self.rooms[room_id][target_id].send_json(message)
                return True
            except Exception as e:
                logger.warning(f"Failed to send direct message to peer {target_id}: {e}")
        return False

manager = RoomSignalingManager()

@router.websocket("/call/{room_id}")
async def websocket_call_endpoint(websocket: WebSocket, room_id: str):
    """
    Unified WebRTC Signaling & AI Deepfake Stream Monitoring WebSocket endpoint.
    Handles peer-to-peer WebRTC SDP exchange (offer, answer, ICE candidates)
    and executes sub-300ms fast-path AI deepfake detection on media chunks.
    """
    client_id = f"peer_{uuid.uuid4().hex[:8]}"
    await manager.connect_client(websocket, room_id, client_id)

    processor = manager.processors[client_id]

    # Notify caller of successful room attachment and send list of existing peers
    existing_peers = [p for p in manager.rooms[room_id].keys() if p != client_id]
    await websocket.send_json({
        "type": "room_joined",
        "room_id": room_id,
        "client_id": client_id,
        "peers": existing_peers
    })

    # Notify existing peers that a new participant joined
    await manager.broadcast_to_room(room_id, client_id, {
        "type": "peer_joined",
        "client_id": client_id,
        "room_id": room_id
    })

    try:
        while True:
            text = await websocket.receive_text()
            data = json.loads(text)
            msg_type = data.get("type")

            # 1. WebRTC Signaling Dispatch
            if msg_type == "offer":
                # Forward SDP offer to target peer
                target_id = data.get("target_id")
                await manager.send_to_peer(room_id, target_id, {
                    "type": "offer",
                    "sdp": data.get("sdp"),
                    "sender_id": client_id,
                    "room_id": room_id
                })

            elif msg_type == "answer":
                # Forward SDP answer to caller peer
                target_id = data.get("target_id")
                await manager.send_to_peer(room_id, target_id, {
                    "type": "answer",
                    "sdp": data.get("sdp"),
                    "sender_id": client_id,
                    "room_id": room_id
                })

            elif msg_type == "ice_candidate":
                # Forward ICE candidate to peers
                target_id = data.get("target_id")
                candidate = data.get("candidate")
                if target_id:
                    await manager.send_to_peer(room_id, target_id, {
                        "type": "ice_candidate",
                        "candidate": candidate,
                        "sender_id": client_id,
                        "room_id": room_id
                    })
                else:
                    await manager.broadcast_to_room(room_id, client_id, {
                        "type": "ice_candidate",
                        "candidate": candidate,
                        "sender_id": client_id,
                        "room_id": room_id
                    })

            # 2. Live Media Analysis Ingestion
            elif msg_type == "audio_chunk":
                pcm_b64 = data.get("audio_base64_pcm", "")
                pcm_format = data.get("format", "float32")
                processor.ingest_audio_pcm_base64(pcm_b64, pcm_format)

            elif msg_type == "video_frame":
                frame_b64 = data.get("frame_base64_jpeg", "")
                processor.ingest_video_frame_base64(frame_b64)

                ts_ms = data.get("timestamp_ms", 0)
                telemetry = processor.process_instantaneous_telemetry(ts_ms)
                await websocket.send_json(telemetry)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "leave_room":
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected from room {room_id}")
    except Exception as e:
        logger.error(f"Error in stream call handling for {client_id}: {e}")
    finally:
        await manager.disconnect_client(client_id)

@router.websocket("/live/{session_id}")
async def websocket_live_stream_legacy(websocket: WebSocket, session_id: str):
    """
    Direct single-session live monitoring endpoint for standalone client HUD testing.
    """
    await websocket.accept()
    processor = StreamProcessor(session_id=session_id)
    logger.info(f"Standalone live stream session connected: {session_id}")

    try:
        while True:
            text = await websocket.receive_text()
            data = json.loads(text)
            msg_type = data.get("type")

            if msg_type == "init":
                await websocket.send_json({
                    "type": "ready",
                    "session_id": session_id,
                    "status": "listening"
                })

            elif msg_type == "audio_chunk":
                pcm_b64 = data.get("audio_base64_pcm", "")
                pcm_format = data.get("format", "float32")
                processor.ingest_audio_pcm_base64(pcm_b64, pcm_format)

            elif msg_type == "video_frame":
                frame_b64 = data.get("frame_base64_jpeg", "")
                processor.ingest_video_frame_base64(frame_b64)

                ts_ms = data.get("timestamp_ms", 0)
                telemetry = processor.process_instantaneous_telemetry(ts_ms)
                await websocket.send_json(telemetry)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"Standalone live session disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Error in standalone live stream: {e}")
        try:
            await websocket.close()
        except Exception:
            pass

@router.get("/rooms/{room_id}/status")
async def get_room_status(room_id: str):
    """Returns the peer count and status of a calling room."""
    peers = list(manager.rooms.get(room_id, {}).keys())
    return {
        "room_id": room_id,
        "is_active": len(peers) > 0,
        "peer_count": len(peers),
        "peers": peers
    }
