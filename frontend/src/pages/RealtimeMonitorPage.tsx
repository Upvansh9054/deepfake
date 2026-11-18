import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Activity,
  Video,
  VideoOff,
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  AlertCircle,
  Users,
  Copy,
  Check,
  Clock,
  Sparkles,
  MonitorUp,
  Radio,
  Eye,
  Lock,
  RefreshCw,
  Info,
  Maximize2,
  Terminal,
} from 'lucide-react';
import { StreamTelemetry } from '../types/detection';

// ICE Configuration with public STUN servers for WebRTC
const RTC_CONFIG: RTCConfiguration = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
  ],
};

type CallMode = 'peer_call' | 'self_audit';

export const RealtimeMonitorPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  // Room & Calling State
  const [callMode, setCallMode] = useState<CallMode>('peer_call');
  const [roomId, setRoomId] = useState(searchParams.get('room') || 'SHIELD-SECURE');
  const [inCall, setInCall] = useState(false);
  const [clientId, setClientId] = useState<string | null>(null);
  const [peerId, setPeerId] = useState<string | null>(null);
  const [callDuration, setCallDuration] = useState(0);
  const [linkCopied, setLinkCopied] = useState(false);

  // Consent & Permission Modal State
  const [hasUserConsent, setHasUserConsent] = useState(false);
  const [consentModalOpen, setConsentModalOpen] = useState(false);

  // Media Controls State
  const [micMuted, setMicMuted] = useState(false);
  const [videoDisabled, setVideoDisabled] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [shieldActive, setShieldActive] = useState(true);
  const [swapPiP, setSwapPiP] = useState(false);

  // Connection Health State
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'reconnecting' | 'disconnected'>('disconnected');
  const [rtcStatus, setRtcStatus] = useState<RTCIceConnectionState>('new');
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // AI Telemetry & HUD State
  const [telemetry, setTelemetry] = useState<StreamTelemetry>({
    type: 'telemetry',
    session_id: 'init',
    timestamp_ms: Date.now(),
    latency_ms: 0,
    fps: 0,
    composite_risk_score: 12.0,
    verdict: 'authentic',
    risk_category: 'Low Risk',
    metrics: {
      audio_synthetic_prob: 0.05,
      video_manipulation_prob: 0.08,
      lip_sync_drift_ms: 14.0,
      spectral_flatness: 0.012,
      faces_detected: 1,
    },
    anomalies: [],
  });

  const [evidenceLog, setEvidenceLog] = useState<Array<{
    id: string;
    timestamp: string;
    message: string;
    severity: 'info' | 'warning' | 'critical';
    score: number;
  }>>([]);

  // Video & Stream Refs
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);

  const localStreamRef = useRef<MediaStream | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const audioProcessorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const videoIntervalRef = useRef<any>(null);
  const callTimerRef = useRef<any>(null);
  const reconnectTimeoutRef = useRef<any>(null);

  // 1. Format Call Duration
  const formatDuration = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const s = secs % 60;
    return `${mins.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // 2. Copy Invite Link
  const copyInviteLink = () => {
    const url = `${window.location.origin}/realtime?room=${encodeURIComponent(roomId)}`;
    navigator.clipboard.writeText(url);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2500);
  };

  // 3. User Consent Flow
  const handleInitiateCall = () => {
    if (!hasUserConsent) {
      setConsentModalOpen(true);
    } else {
      startCall();
    }
  };

  const handleGrantConsentAndStart = () => {
    setHasUserConsent(true);
    setConsentModalOpen(false);
    startCall();
  };

  // 4. Initialize Media Streams (Camera & Mic)
  const initializeUserMedia = async (): Promise<MediaStream> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { max: 15 },
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });

      localStreamRef.current = stream;
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }
      return stream;
    } catch (err: any) {
      const msg = err.name === 'NotAllowedError'
        ? 'Camera and microphone access was denied by your browser. Please allow permissions in your address bar.'
        : `Media access error: ${err.message}`;
      setConnectionError(msg);
      throw new Error(msg);
    }
  };

  // 5. Setup WebRTC Peer Connection
  const createPeerConnection = (stream: MediaStream): RTCPeerConnection => {
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
    }

    const pc = new RTCPeerConnection(RTC_CONFIG);
    peerConnectionRef.current = pc;

    // Add local tracks
    stream.getTracks().forEach((track) => {
      pc.addTrack(track, stream);
    });

    // Remote stream receiver
    pc.ontrack = (event) => {
      if (remoteVideoRef.current && event.streams[0]) {
        remoteVideoRef.current.srcObject = event.streams[0];
      }
    };

    // ICE Candidate handler
    pc.onicecandidate = (event) => {
      if (event.candidate && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'ice_candidate',
          candidate: event.candidate,
          target_id: peerId,
        }));
      }
    };

    // Connection state listeners
    pc.oniceconnectionstatechange = () => {
      setRtcStatus(pc.iceConnectionState);
      if (pc.iceConnectionState === 'disconnected' || pc.iceConnectionState === 'failed') {
        logEvidence('WebRTC network connection degraded or peer disconnected.', 'warning', 30);
      }
    };

    return pc;
  };

  // 6. Connect WebSocket for Signaling & Live Telemetry
  const connectWebSocket = useCallback((stream: MediaStream) => {
    let wsHost = window.location.host;
    let wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    if (import.meta.env.VITE_API_URL) {
      try {
        const apiUrl = new URL(import.meta.env.VITE_API_URL as string);
        wsHost = apiUrl.host;
        wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      } catch {
        // fallback to window.location
      }
    }
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/stream/call/${encodeURIComponent(roomId)}`;

    setWsStatus('connecting');
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('connected');
      setConnectionError(null);
      logEvidence(`Connected to Deepfake Shield AI Guard for room [${roomId}]`, 'info', 0);
    };

    ws.onmessage = async (event) => {
      try {
        const msg = JSON.parse(event.data);

        // A. Room Signaling Protocol
        if (msg.type === 'room_joined') {
          setClientId(msg.client_id);
          // If there are existing peers, initiate WebRTC offer to the first peer
          if (msg.peers && msg.peers.length > 0) {
            const targetPeer = msg.peers[0];
            setPeerId(targetPeer);
            await createAndSendOffer(targetPeer);
          }
        } else if (msg.type === 'peer_joined') {
          setPeerId(msg.client_id);
          logEvidence(`Participant joined: ${msg.client_id}. Initiating WebRTC handshake...`, 'info', 0);
        } else if (msg.type === 'peer_left') {
          logEvidence(`Participant left: ${msg.client_id}`, 'info', 0);
          setPeerId(null);
          if (remoteVideoRef.current) {
            remoteVideoRef.current.srcObject = null;
          }
        } else if (msg.type === 'offer') {
          setPeerId(msg.sender_id);
          await handleReceiveOffer(msg.sdp, msg.sender_id);
        } else if (msg.type === 'answer') {
          await handleReceiveAnswer(msg.sdp);
        } else if (msg.type === 'ice_candidate') {
          if (peerConnectionRef.current && msg.candidate) {
            await peerConnectionRef.current.addIceCandidate(new RTCIceCandidate(msg.candidate));
          }
        }

        // B. Real-Time Neural Telemetry
        else if (msg.type === 'telemetry') {
          handleIncomingTelemetry(msg);
        }
      } catch (e) {
        console.error('Error handling WebSocket message', e);
      }
    };

    ws.onerror = () => {
      setWsStatus('reconnecting');
      setConnectionError('WebSocket telemetry connection encountered an error.');
    };

    ws.onclose = () => {
      setWsStatus('disconnected');
    };
  }, [roomId, peerId]);

  // 7. WebRTC Offer / Answer Handlers
  const createAndSendOffer = async (targetPeer: string) => {
    const pc = peerConnectionRef.current;
    if (!pc) return;
    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'offer',
          sdp: offer,
          target_id: targetPeer,
        }));
      }
    } catch (err) {
      console.error('Failed to create WebRTC offer', err);
    }
  };

  const handleReceiveOffer = async (sdp: RTCSessionDescriptionInit, senderId: string) => {
    const pc = peerConnectionRef.current;
    if (!pc) return;
    try {
      await pc.setRemoteDescription(new RTCSessionDescription(sdp));
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'answer',
          sdp: answer,
          target_id: senderId,
        }));
      }
    } catch (err) {
      console.error('Failed to process WebRTC offer', err);
    }
  };

  const handleReceiveAnswer = async (sdp: RTCSessionDescriptionInit) => {
    const pc = peerConnectionRef.current;
    if (!pc) return;
    try {
      await pc.setRemoteDescription(new RTCSessionDescription(sdp));
    } catch (err) {
      console.error('Failed to set remote description answer', err);
    }
  };

  // 8. Stream Ingestion Pipeline (Audio Worklet/ScriptProcessor & Video Canvas Grabber)
  const startMediaIngestion = (stream: MediaStream) => {
    // A. Audio Ingestion (16kHz Float32 PCM chunks via Web Audio API)
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      // 4096 buffer size gives ~256ms audio chunks at 16kHz
      const processorNode = audioCtx.createScriptProcessor(4096, 1, 1);
      audioProcessorNodeRef.current = processorNode;

      processorNode.onaudioprocess = (e) => {
        if (!shieldActive || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        const inputBuffer = e.inputBuffer.getChannelData(0);
        // Encode Float32Array to Base64
        const uint8Bytes = new Uint8Array(inputBuffer.buffer);
        let binaryStr = '';
        const len = uint8Bytes.byteLength;
        for (let i = 0; i < len; i++) {
          binaryStr += String.fromCharCode(uint8Bytes[i]);
        }
        const b64 = window.btoa(binaryStr);

        wsRef.current.send(JSON.stringify({
          type: 'audio_chunk',
          audio_base64_pcm: b64,
          format: 'float32',
          timestamp_ms: Date.now(),
        }));
      };

      source.connect(processorNode);
      processorNode.connect(audioCtx.destination);
    } catch (e) {
      console.warn('AudioContext ingestion initialization error:', e);
    }

    // B. Video Keyframe Sampling (3-5 FPS downsampled canvas grabber)
    const canvas = document.createElement('canvas');
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext('2d');

    videoIntervalRef.current = setInterval(() => {
      if (!shieldActive || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

      // Inspect remote peer video if connected, or inspect local/screen video in self-audit mode
      const targetVideo = (peerId && remoteVideoRef.current && remoteVideoRef.current.videoWidth > 0)
        ? remoteVideoRef.current
        : localVideoRef.current;

      if (targetVideo && targetVideo.videoWidth > 0 && ctx) {
        ctx.drawImage(targetVideo, 0, 0, canvas.width, canvas.height);
        const jpegDataUrl = canvas.toDataURL('image/jpeg', 0.65);

        wsRef.current.send(JSON.stringify({
          type: 'video_frame',
          frame_base64_jpeg: jpegDataUrl,
          timestamp_ms: Date.now(),
        }));
      }
    }, 250); // 4 FPS
  };

  // 9. Process Inbound AI Telemetry & Render Visual Bounding Box
  const handleIncomingTelemetry = (data: StreamTelemetry) => {
    setTelemetry(data);

    // Draw visual bounding box on overlay canvas
    const overlay = overlayCanvasRef.current;
    if (overlay) {
      const ctx = overlay.getContext('2d');
      if (ctx) {
        ctx.clearRect(0, 0, overlay.width, overlay.height);

        if (data.face_bbox) {
          const { x, y, w, h } = data.face_bbox;
          const rectX = x * overlay.width;
          const rectY = y * overlay.height;
          const rectW = w * overlay.width;
          const rectH = h * overlay.height;

          const isCritical = data.composite_risk_score >= 65;
          const isWarning = data.composite_risk_score >= 35 && !isCritical;

          ctx.lineWidth = 2.5;
          ctx.strokeStyle = isCritical ? '#EF4444' : isWarning ? '#F59E0B' : '#10B981';
          ctx.fillStyle = isCritical ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.08)';

          ctx.strokeRect(rectX, rectY, rectW, rectH);
          ctx.fillRect(rectX, rectY, rectW, rectH);

          // Draw biometric tag
          ctx.fillStyle = isCritical ? '#EF4444' : isWarning ? '#F59E0B' : '#10B981';
          ctx.font = 'bold 11px monospace';
          const label = `BIOMETRIC HUD: ${data.risk_category?.toUpperCase() || 'SCANNING'} (${data.composite_risk_score}%)`;
          ctx.fillText(label, rectX + 4, Math.max(16, rectY - 6));
        }
      }
    }

    // Log significant anomalies
    if (data.anomalies && data.anomalies.length > 0) {
      data.anomalies.forEach((ano) => {
        const severity = ano.severity === 'high' ? 'critical' : 'warning';
        logEvidence(ano.message || `Detected anomaly: ${ano.type}`, severity, data.composite_risk_score);
      });
    }
  };

  // 10. Helper to record evidence in ledger
  const logEvidence = (message: string, severity: 'info' | 'warning' | 'critical', score: number) => {
    const timestamp = new Date().toLocaleTimeString();
    setEvidenceLog((prev) => [
      {
        id: Math.random().toString(36).slice(2, 9),
        timestamp,
        message,
        severity,
        score,
      },
      ...prev.slice(0, 40),
    ]);
  };

  // 11. Start Call Session
  const startCall = async () => {
    setConnectionError(null);
    try {
      const stream = await initializeUserMedia();
      createPeerConnection(stream);
      connectWebSocket(stream);
      startMediaIngestion(stream);

      setInCall(true);
      setCallDuration(0);
      callTimerRef.current = setInterval(() => {
        setCallDuration((c) => c + 1);
      }, 1000);
    } catch (err: any) {
      console.error('Call initialization failed', err);
    }
  };

  // 12. End Call Session
  const endCall = () => {
    // Stop local stream
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => track.stop());
      localStreamRef.current = null;
    }
    // Stop screen stream
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach((track) => track.stop());
      screenStreamRef.current = null;
    }
    // Close WebRTC
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    // Close AudioContext
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    clearInterval(videoIntervalRef.current as any);
    clearInterval(callTimerRef.current as any);
    clearTimeout(reconnectTimeoutRef.current as any);

    if (localVideoRef.current) localVideoRef.current.srcObject = null;
    if (remoteVideoRef.current) remoteVideoRef.current.srcObject = null;

    setInCall(false);
    setPeerId(null);
    setIsScreenSharing(false);
    setWsStatus('disconnected');
    logEvidence('Call session terminated.', 'info', 0);
  };

  // 13. Call Controls (Mute Mic, Toggle Video, Screen Share)
  const toggleMute = () => {
    if (localStreamRef.current) {
      const audioTrack = localStreamRef.current.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setMicMuted(!audioTrack.enabled);
      }
    }
  };

  const toggleVideo = () => {
    if (localStreamRef.current) {
      const videoTrack = localStreamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setVideoDisabled(!videoTrack.enabled);
      }
    }
  };

  const toggleScreenShare = async () => {
    if (isScreenSharing) {
      // Revert to camera
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach((t) => t.stop());
        screenStreamRef.current = null;
      }
      if (localStreamRef.current && localVideoRef.current) {
        localVideoRef.current.srcObject = localStreamRef.current;
        const videoTrack = localStreamRef.current.getVideoTracks()[0];
        if (peerConnectionRef.current && videoTrack) {
          const sender = peerConnectionRef.current.getSenders().find((s) => s.track?.kind === 'video');
          if (sender) sender.replaceTrack(videoTrack);
        }
      }
      setIsScreenSharing(false);
    } else {
      // Start Screen Share
      try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
        });
        screenStreamRef.current = screenStream;
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = screenStream;
        }

        const screenTrack = screenStream.getVideoTracks()[0];
        if (peerConnectionRef.current && screenTrack) {
          const sender = peerConnectionRef.current.getSenders().find((s) => s.track?.kind === 'video');
          if (sender) sender.replaceTrack(screenTrack);
        }

        screenTrack.onended = () => {
          toggleScreenShare();
        };

        setIsScreenSharing(true);
      } catch (err: any) {
        console.warn('Screen share cancelled or failed:', err);
      }
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      endCall();
    };
  }, []);

  const riskScore = telemetry.composite_risk_score;
  const isCritical = riskScore >= 65;
  const isWarning = riskScore >= 35 && !isCritical;

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      {/* Top Banner & Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-5 rounded-2xl bg-gradient-to-r from-gray-900 via-[#111827] to-cyan-950/40 border border-gray-800 shadow-xl">
        <div>
          <div className="flex items-center space-x-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <Radio className="w-4 h-4 animate-pulse text-cyan-400" />
            <span>WebRTC Encrypted Live Calling &bull; Real-Time AI Deepfake Monitor</span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold text-gray-100 flex items-center space-x-2">
            <span>Live Video Call &amp; Voice Clone Shield</span>
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Zero third-party dependency browser calling with sub-300ms continuous neural speech, facial seam, and lip-sync drift inspection.
          </p>
        </div>

        {/* Room & Call Setup Action */}
        <div className="flex flex-wrap items-center gap-2.5">
          {!inCall ? (
            <div className="flex items-center space-x-2 bg-gray-900/90 border border-gray-800 p-1.5 rounded-xl">
              <input
                type="text"
                value={roomId}
                onChange={(e) => setRoomId(e.target.value.toUpperCase())}
                placeholder="ROOM-ID"
                className="bg-transparent px-3 py-1.5 text-xs font-mono font-bold text-cyan-400 uppercase focus:outline-none w-36"
              />
              <button
                onClick={handleInitiateCall}
                className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-lg shadow-cyan-600/20"
              >
                <Phone className="w-3.5 h-3.5" />
                <span>Start Video Call</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-xs font-mono">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <span className="text-gray-300 font-semibold">{formatDuration(callDuration)}</span>
                <span className="text-gray-500">|</span>
                <span className="text-cyan-400 font-bold">{roomId}</span>
              </div>
              <button
                onClick={copyInviteLink}
                className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-medium transition flex items-center space-x-1.5"
                title="Copy Shareable Call Link"
              >
                {linkCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-cyan-400" />}
                <span>{linkCopied ? 'Link Copied!' : 'Invite Peer'}</span>
              </button>
              <button
                onClick={endCall}
                className="px-4 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-lg shadow-red-600/25"
              >
                <PhoneOff className="w-3.5 h-3.5" />
                <span>End Call</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {connectionError && (
        <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/50 flex items-start space-x-3 text-xs text-red-300">
          <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
          <span>{connectionError}</span>
        </div>
      )}

      {/* Main Video Call Viewport & Evidence Ledger */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Video Stage */}
        <div className="lg:col-span-2 space-y-4">
          <div className="relative rounded-2xl bg-black border border-gray-800 overflow-hidden shadow-2xl aspect-video flex items-center justify-center">
            {/* Main Stage Video: Remote Peer Video (or Local Video in Self-Audit Mode) */}
            <video
              ref={peerId ? remoteVideoRef : localVideoRef}
              autoPlay
              playsInline
              muted={!peerId} // Mute self video to avoid acoustic feedback
              className="w-full h-full object-cover"
            />

            {/* Canvas Overlay for Face Bounding Box & HUD Highlights */}
            <canvas
              ref={overlayCanvasRef}
              width={640}
              height={480}
              className="absolute inset-0 w-full h-full pointer-events-none z-10"
            />

            {/* Picture-in-Picture Self Video (When Remote Peer is Active) */}
            {inCall && peerId && (
              <div
                onClick={() => setSwapPiP(!swapPiP)}
                className="absolute top-4 right-4 w-40 sm:w-48 aspect-video rounded-xl overflow-hidden border-2 border-gray-700 bg-gray-900 shadow-2xl z-20 cursor-pointer hover:border-cyan-400 transition"
                title="Click to swap viewports"
              >
                <video
                  ref={swapPiP ? remoteVideoRef : localVideoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
                <div className="absolute bottom-1 left-1.5 bg-black/60 px-1.5 py-0.5 rounded text-[9px] font-mono text-gray-300">
                  {swapPiP ? 'Remote' : 'You (Local)'}
                </div>
              </div>
            )}

            {/* Over-the-Stream Threat Warning Banner */}
            {inCall && isCritical && (
              <div className="absolute top-4 left-4 right-4 z-30 p-3 rounded-xl bg-red-950/90 border border-red-500 text-red-100 flex items-center space-x-3 shadow-2xl animate-pulse">
                <ShieldAlert className="w-6 h-6 text-red-400 flex-shrink-0" />
                <div className="text-xs">
                  <p className="font-bold uppercase tracking-wider text-red-200">
                    High-Risk Deepfake Warning ({riskScore}%)
                  </p>
                  <p className="text-[11px] text-red-300">
                    Severe synthetic voice characteristics or facial boundary seam gradients detected.
                  </p>
                </div>
              </div>
            )}

            {inCall && isWarning && (
              <div className="absolute top-4 left-4 right-4 z-30 p-2.5 rounded-xl bg-amber-950/80 border border-amber-500/80 text-amber-100 flex items-center space-x-3 shadow-xl">
                <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
                <div className="text-xs">
                  <p className="font-bold text-amber-200 uppercase">
                    Suspicious Stream Anomaly ({riskScore}%)
                  </p>
                  <p className="text-[10px] text-amber-300">
                    Audio-visual lip-sync temporal drift ({telemetry.metrics.lip_sync_drift_ms}ms) exceeds standard organic range.
                  </p>
                </div>
              </div>
            )}

            {/* Offline or Idle Placeholder */}
            {!inCall && (
              <div className="text-center p-8 space-y-3 text-gray-400 z-10">
                <div className="w-14 h-14 rounded-full bg-gray-900 border border-gray-700 flex items-center justify-center mx-auto text-cyan-400">
                  <Video className="w-7 h-7" />
                </div>
                <h3 className="text-sm font-bold text-gray-200">Secure Calling Room Ready</h3>
                <p className="text-xs text-gray-500 max-w-sm">
                  Click <strong>Start Video Call</strong> to grant media permissions and establish peer-to-peer WebRTC video with real-time deepfake defense.
                </p>
              </div>
            )}

            {/* Live Telemetry Ticker (Bottom HUD Overlay) */}
            {inCall && (
              <div className="video-telemetry-hud absolute bottom-3 left-3 right-3 z-20 flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-xl bg-slate-950/90 backdrop-blur-md border border-slate-700/80 text-[11px] font-mono shadow-2xl text-white">
                <div className="flex items-center space-x-3">
                  <div className="flex items-center space-x-1.5">
                    <span className={`w-2.5 h-2.5 rounded-full ${
                      isCritical ? 'bg-red-500 animate-ping' : isWarning ? 'bg-amber-500' : 'bg-emerald-400'
                    }`} />
                    <span className="font-bold text-white tracking-wide">
                      THREAT: {riskScore}% ({telemetry.risk_category})
                    </span>
                  </div>
                  <span className="text-slate-500">|</span>
                  <div className="text-sky-300 font-medium">
                    Drift: <span className="font-bold text-white">{telemetry.metrics.lip_sync_drift_ms}ms</span>
                  </div>
                </div>

                <div className="flex items-center space-x-3 text-slate-300 text-[10px]">
                  <span>FPS: <strong className="text-white font-bold">{telemetry.fps}</strong></span>
                  <span>Latency: <strong className="text-emerald-300 font-bold">{telemetry.latency_ms}ms</strong></span>
                  <span className="hidden sm:inline">RTC: <strong className="text-sky-200 font-bold">{rtcStatus}</strong></span>
                </div>
              </div>
            )}
          </div>

          {/* Call Controls Bar */}
          <div className="p-3.5 rounded-2xl bg-[#111827] border border-gray-800 flex items-center justify-between shadow-xl">
            <div className="flex items-center space-x-2">
              <button
                onClick={toggleMute}
                disabled={!inCall}
                className={`p-3 rounded-xl border text-xs font-semibold transition flex items-center space-x-2 ${
                  micMuted
                    ? 'bg-red-950/60 border-red-500/50 text-red-400'
                    : 'bg-gray-800 hover:bg-gray-700 border-gray-700 text-gray-200'
                } disabled:opacity-40`}
                title={micMuted ? 'Unmute Microphone' : 'Mute Microphone'}
              >
                {micMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4 text-cyan-400" />}
              </button>

              <button
                onClick={toggleVideo}
                disabled={!inCall}
                className={`p-3 rounded-xl border text-xs font-semibold transition flex items-center space-x-2 ${
                  videoDisabled
                    ? 'bg-red-950/60 border-red-500/50 text-red-400'
                    : 'bg-gray-800 hover:bg-gray-700 border-gray-700 text-gray-200'
                } disabled:opacity-40`}
                title={videoDisabled ? 'Enable Video Camera' : 'Disable Video Camera'}
              >
                {videoDisabled ? <VideoOff className="w-4 h-4" /> : <Video className="w-4 h-4 text-indigo-400" />}
              </button>

              <button
                onClick={toggleScreenShare}
                disabled={!inCall}
                className={`p-3 rounded-xl border text-xs font-semibold transition flex items-center space-x-2 ${
                  isScreenSharing
                    ? 'bg-purple-950/60 border-purple-500/50 text-purple-300'
                    : 'bg-gray-800 hover:bg-gray-700 border-gray-700 text-gray-200'
                } disabled:opacity-40`}
                title={isScreenSharing ? 'Stop Screen Share' : 'Inspect External Window / Screen Share'}
              >
                <MonitorUp className="w-4 h-4 text-purple-400" />
              </button>
            </div>

            {/* AI Guard Active Pill */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShieldActive(!shieldActive)}
                disabled={!inCall}
                className={`px-3 py-2 rounded-xl border text-xs font-bold transition flex items-center space-x-2 ${
                  shieldActive
                    ? 'bg-cyan-950/40 border-cyan-500/40 text-cyan-300'
                    : 'bg-gray-800/80 border-gray-700 text-gray-400'
                } disabled:opacity-40`}
              >
                <Shield className="w-4 h-4 text-cyan-400" />
                <span>AI Shield: {shieldActive ? 'ON' : 'PAUSED'}</span>
              </button>

              {inCall && (
                <button
                  onClick={endCall}
                  className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold transition flex items-center space-x-1.5"
                >
                  <PhoneOff className="w-4 h-4" />
                  <span>Leave</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Right Col: Live Forensic Telemetry & Evidence Ledger */}
        <div className="space-y-4">
          {/* Signal Decomposition Meters */}
          <div className="p-5 rounded-2xl bg-[#111827] border border-gray-800 shadow-xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-gray-800">
              <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-gray-300">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <span>Live Signal Indicators</span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-800 text-gray-400">
                {wsStatus.toUpperCase()}
              </span>
            </div>

            {/* Voice Synthesis Risk Meter */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-gray-400 flex items-center space-x-1.5">
                  <Mic className="w-3 h-3 text-cyan-400" />
                  <span>Voice Clone / TTS Likelihood</span>
                </span>
                <span className="font-mono font-bold text-cyan-400">
                  {Math.round(telemetry.metrics.audio_synthetic_prob * 100)}%
                </span>
              </div>
              <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-cyan-500 h-full transition-all duration-300"
                  style={{ width: `${telemetry.metrics.audio_synthetic_prob * 100}%` }}
                />
              </div>
            </div>

            {/* Facial Boundary Seam Disparity */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-gray-400 flex items-center space-x-1.5">
                  <Video className="w-3 h-3 text-indigo-400" />
                  <span>Facial Seam &amp; FFT Residuals</span>
                </span>
                <span className="font-mono font-bold text-indigo-400">
                  {Math.round(telemetry.metrics.video_manipulation_prob * 100)}%
                </span>
              </div>
              <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-indigo-500 h-full transition-all duration-300"
                  style={{ width: `${telemetry.metrics.video_manipulation_prob * 100}%` }}
                />
              </div>
            </div>

            {/* Lip-Sync Drift Meter */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-gray-400 flex items-center space-x-1.5">
                  <Clock className="w-3 h-3 text-purple-400" />
                  <span>Audio-Visual Lip-Sync Drift</span>
                </span>
                <span className="font-mono font-bold text-purple-400">
                  {telemetry.metrics.lip_sync_drift_ms} ms
                </span>
              </div>
              <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-purple-500 h-full transition-all duration-300"
                  style={{ width: `${Math.min(100, (telemetry.metrics.lip_sync_drift_ms / 200) * 100)}%` }}
                />
              </div>
            </div>

            {/* Hardware / Latency Metric */}
            <div className="pt-2 border-t border-gray-800 text-[10px] font-mono text-gray-500 space-y-1">
              <div className="flex justify-between">
                <span>Inference Latency</span>
                <span className="text-emerald-400 font-bold">{telemetry.latency_ms} ms (Sub-300ms)</span>
              </div>
              <div className="flex justify-between">
                <span>Sampling Cadence</span>
                <span className="text-gray-300">16 kHz PCM &bull; 4 FPS Keyframes</span>
              </div>
            </div>
          </div>

          {/* Chronological Evidence Ledger */}
          <div className="p-5 rounded-2xl bg-[#111827] border border-gray-800 shadow-xl space-y-3 flex flex-col h-72">
            <div className="flex items-center justify-between pb-2 border-b border-gray-800">
              <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-gray-300">
                <Terminal className="w-4 h-4 text-cyan-400" />
                <span>Evidence &amp; Threat Audit Log</span>
              </div>
              <span className="text-[10px] font-mono text-gray-500">
                {evidenceLog.length} events
              </span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1 text-xs font-mono">
              {evidenceLog.length === 0 ? (
                <div className="text-center py-10 text-gray-600 text-xs font-sans">
                  No threat anomalies recorded yet. Call telemetry active.
                </div>
              ) : (
                evidenceLog.map((ev) => (
                  <div
                    key={ev.id}
                    className={`p-2 rounded-lg border text-[11px] leading-relaxed ${
                      ev.severity === 'critical'
                        ? 'bg-red-950/40 border-red-500/40 text-red-200'
                        : ev.severity === 'warning'
                        ? 'bg-amber-950/30 border-amber-500/30 text-amber-200'
                        : 'bg-gray-900/60 border-gray-800 text-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[10px] opacity-75 mb-0.5">
                      <span>[{ev.timestamp}]</span>
                      <span className="uppercase font-bold">{ev.severity}</span>
                    </div>
                    <p>{ev.message}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* User Consent & Privacy Permission Modal */}
      {consentModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-cyan-500/40 max-w-lg w-full rounded-2xl p-6 space-y-4 shadow-2xl">
            <div className="flex items-center space-x-3 text-cyan-400">
              <Lock className="w-6 h-6" />
              <h3 className="text-base font-bold text-gray-100">
                Deepfake Shield Media Access &amp; AI Analysis Consent
              </h3>
            </div>

            <div className="text-xs text-gray-300 space-y-2.5 leading-relaxed">
              <p>
                To provide real-time voice clone and deepfake defense, Deepfake Shield will request browser access to your <strong>microphone</strong> and <strong>camera</strong>.
              </p>
              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800 space-y-1.5 text-[11px] text-gray-400">
                <div className="flex items-start space-x-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <span><strong>Manageable Segments:</strong> Video is sampled at 4 FPS and audio is processed in 250ms circular buffers.</span>
                </div>
                <div className="flex items-start space-x-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <span><strong>Zero Persistent Video Storage:</strong> Live stream frames are evaluated in-memory and discarded immediately after telemetry extraction.</span>
                </div>
                <div className="flex items-start space-x-2">
                  <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <span><strong>Consent Gate:</strong> No audio or video is transmitted or inspected without your explicit consent.</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-gray-800">
              <button
                type="button"
                onClick={() => setConsentModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleGrantConsentAndStart}
                className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition flex items-center space-x-1.5 shadow-lg shadow-cyan-600/20"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Grant Permission &amp; Start Call</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
