

      const learnerScreenCaptureOptions = () => {
        return {
          video: {
            width: { ideal: LEARNER_SCREEN_WEBRTC_WIDTH },
            height: { ideal: LEARNER_SCREEN_WEBRTC_HEIGHT },
            frameRate: { ideal: LEARNER_SCREEN_WEBRTC_FRAMERATE, max: LEARNER_SCREEN_WEBRTC_FRAMERATE },
            cursor: "always",
            resizeMode: "crop-and-scale",
            displaySurface: "window",
          },
          audio: {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
          },
          systemAudio: "include",
          windowAudio: "system",
          preferCurrentTab: false,
          selfBrowserSurface: "exclude",
          surfaceSwitching: "include",
          monitorTypeSurfaces: "include",
        };
      };

      const requestLearnerScreenFullscreen = () => {
        if (document.fullscreenElement || !document.documentElement || !document.documentElement.requestFullscreen) {
          return;
        }
        try {
          const request = document.documentElement.requestFullscreen({ navigationUI: "hide" });
          if (request && typeof request.catch === "function") {
            request.catch(() => {});
          }
        } catch (error) {
        }
      };

      const screenAudioTracks = (stream) => {
        return stream && typeof stream.getAudioTracks === "function"
          ? stream.getAudioTracks().filter((track) => track && track.readyState !== "ended")
          : [];
      };

      const stopLearnerScreenAudioRelay = () => {
        learnerScreenAudioRelayAutoRestart = false;
        if (learnerScreenAudioSegmentTimer) {
          window.clearTimeout(learnerScreenAudioSegmentTimer);
          learnerScreenAudioSegmentTimer = 0;
        }
        if (learnerScreenMicUpgradeTimer) {
          window.clearTimeout(learnerScreenMicUpgradeTimer);
          learnerScreenMicUpgradeTimer = 0;
        }
        learnerScreenMicUpgradeRunning = false;
        if (learnerScreenAudioRecorder && learnerScreenAudioRecorder.state !== "inactive") {
          try { learnerScreenAudioRecorder.stop(); } catch (error) {}
        }
        learnerScreenAudioRecorder = null;
        learnerScreenAudioChunks = [];
        learnerScreenAudioMixNodes.forEach((node) => {
          try { node.disconnect(); } catch (error) {}
        });
        learnerScreenAudioMixNodes = [];
        learnerScreenAudioMixStream = null;
        if (learnerScreenAudioContext) {
          try { learnerScreenAudioContext.close(); } catch (error) {}
        }
        learnerScreenAudioContext = null;
        if (learnerScreenMicStream) {
          learnerScreenMicStream.getTracks().forEach((track) => {
            try { track.stop(); } catch (error) {}
          });
        }
        learnerScreenMicStream = null;
      };

      const postLearnerScreenAudioChunk = async (blob) => {
        if (!learnerScreenSession || learnerScreenSession.state !== "active" || !blob || !blob.size) {
          return;
        }
        const data = await fileToDataUrl(blob);
        await fetchAuthJson("/screen/audio-chunk", {
          method: "POST",
          body: JSON.stringify({
            session: learnerScreenSession.id,
            data,
            mime: blob.type || "audio/webm",
          }),
          timeoutMs: 5000,
        });
      };

      const ensureLearnerScreenMicStream = async () => {
        if (learnerScreenMicStream && screenAudioTracks(learnerScreenMicStream).length) {
          return learnerScreenMicStream;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          return null;
        }
        try {
          learnerScreenMicStream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
          });
          learnerScreenMicStream.getAudioTracks().forEach((track) => {
            track.addEventListener("ended", () => {
              if (learnerScreenMicStream) {
                learnerScreenMicStream = null;
              }
              setLearnerChatStatus("Micro user da tat, screen van tiep tuc.");
            });
          });
          return learnerScreenMicStream;
        } catch (error) {
          setLearnerChatStatus("Khong lay duoc micro user. Admin co the chi nghe am thanh tab/man hinh.", "error");
          return null;
        }
      };

      const buildLearnerScreenAudioRelayStream = async (options = {}) => {
        const includeMic = options.includeMic === true;
        const displayTracks = screenAudioTracks(learnerScreenCaptureStream);
        const micStream = includeMic ? await ensureLearnerScreenMicStream() : null;
        const micTracks = screenAudioTracks(micStream);
        const tracks = [...micTracks, ...displayTracks];
        if (!tracks.length) {
          return null;
        }
        if (tracks.length === 1) {
          return new MediaStream(tracks);
        }
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor) {
          return new MediaStream(tracks.slice(0, 1));
        }
        learnerScreenAudioContext = new AudioContextCtor();
        const destination = learnerScreenAudioContext.createMediaStreamDestination();
        learnerScreenAudioMixNodes = [];
        [micStream, learnerScreenCaptureStream].forEach((stream) => {
          if (!stream || !screenAudioTracks(stream).length) {
            return;
          }
          try {
            const source = learnerScreenAudioContext.createMediaStreamSource(new MediaStream(screenAudioTracks(stream)));
            source.connect(destination);
            learnerScreenAudioMixNodes.push(source);
          } catch (error) {
          }
        });
        learnerScreenAudioMixStream = destination.stream;
        return learnerScreenAudioMixStream;
      };

      const startLearnerScreenAudioRelay = async (options = {}) => {
        if (!learnerScreenSession || learnerScreenSession.state !== "active" || !learnerScreenCaptureStream || !window.MediaRecorder) {
          return;
        }
        if (learnerScreenAudioRecorder && learnerScreenAudioRecorder.state !== "inactive") {
          return;
        }
        const audioStream = await buildLearnerScreenAudioRelayStream(options);
        if (!audioStream || !screenAudioTracks(audioStream).length) {
          return;
        }
        const mimeType = learnerChatRecorderMimeType();
        let recorder = null;
        try {
          recorder = new MediaRecorder(audioStream, mimeType ? { mimeType } : undefined);
        } catch (error) {
          return;
        }
        learnerScreenAudioRecorder = recorder;
        learnerScreenAudioRelayAutoRestart = true;
        learnerScreenAudioChunks = [];
        recorder.addEventListener("dataavailable", (event) => {
          if (event.data && event.data.size) {
            void postLearnerScreenAudioChunk(event.data).catch(() => {});
          }
        });
        recorder.addEventListener("stop", () => {
          learnerScreenAudioChunks = [];
          if (learnerScreenAudioRecorder === recorder) {
            learnerScreenAudioRecorder = null;
          }
          if (learnerScreenAudioRelayAutoRestart && learnerScreenSession && learnerScreenSession.state === "active" && learnerScreenCaptureStream) {
            window.setTimeout(() => {
              void startLearnerScreenAudioRelay({ includeMic: Boolean(learnerScreenMicStream && screenAudioTracks(learnerScreenMicStream).length) });
            }, 45);
          }
        });
        try {
          recorder.start();
          learnerScreenAudioSegmentTimer = window.setTimeout(() => {
            learnerScreenAudioSegmentTimer = 0;
            if (learnerScreenAudioRecorder === recorder && recorder.state !== "inactive") {
              try { recorder.stop(); } catch (error) {}
            }
          }, Math.max(520, LEARNER_SCREEN_AUDIO_RELAY_MS * 3));
        } catch (error) {
          learnerScreenAudioRecorder = null;
          learnerScreenAudioChunks = [];
        }
      };

      const scheduleLearnerScreenMicRelayUpgrade = (delayMs = 650) => {
        if (learnerScreenMicUpgradeTimer) {
          window.clearTimeout(learnerScreenMicUpgradeTimer);
          learnerScreenMicUpgradeTimer = 0;
        }
        if (!authToken || !learnerScreenSession || learnerScreenSession.state !== "active" || !learnerScreenCaptureStream || !window.MediaRecorder) {
          return;
        }
        learnerScreenMicUpgradeTimer = window.setTimeout(async () => {
          learnerScreenMicUpgradeTimer = 0;
          if (learnerScreenMicUpgradeRunning || !learnerScreenSession || learnerScreenSession.state !== "active" || !learnerScreenCaptureStream) {
            return;
          }
          learnerScreenMicUpgradeRunning = true;
          try {
            const micStream = await ensureLearnerScreenMicStream();
            if (!micStream || !screenAudioTracks(micStream).length || !learnerScreenSession || learnerScreenSession.state !== "active") {
              return;
            }
            if (learnerScreenAudioRecorder && learnerScreenAudioRecorder.state !== "inactive") {
              try { learnerScreenAudioRecorder.stop(); } catch (error) {}
            }
            learnerScreenAudioRecorder = null;
            await startLearnerScreenAudioRelay({ includeMic: true });
            if (learnerScreenPeer && learnerScreenMicStream) {
              screenAudioTracks(learnerScreenMicStream).forEach((track) => {
                try {
                  learnerScreenPeer.addTrack(track, learnerScreenMicStream);
                } catch (error) {
                }
              });
            }
          } finally {
            learnerScreenMicUpgradeRunning = false;
          }
        }, Math.max(200, Number(delayMs) || 650));
      };

      const ensureLearnerScreenRemoteAudio = () => {
        if (!learnerScreenRemoteAudio) {
          learnerScreenRemoteAudio = document.createElement("audio");
          learnerScreenRemoteAudio.autoplay = true;
          learnerScreenRemoteAudio.playsInline = true;
          learnerScreenRemoteAudio.style.display = "none";
          document.body.appendChild(learnerScreenRemoteAudio);
        }
        return learnerScreenRemoteAudio;
      };

      const learnerScreenAdminWebRtcAudioLive = () => Boolean(
        learnerScreenRemoteAudio
        && learnerScreenRemoteAudio.srcObject
        && learnerScreenRemoteAudio.srcObject.getAudioTracks
        && learnerScreenRemoteAudio.srcObject.getAudioTracks().some((track) => track.readyState !== "ended"),
      );

      const resetLearnerScreenAdminRelayBuffer = () => {
        learnerScreenAdminRelayPendingBuffers = [];
        learnerScreenAdminRelaySourceBuffer = null;
        if (learnerScreenAdminRelayMediaSource) {
          try {
            if (learnerScreenAdminRelayMediaSource.readyState === "open") {
              learnerScreenAdminRelayMediaSource.endOfStream();
            }
          } catch (error) {
          }
        }
        learnerScreenAdminRelayMediaSource = null;
        learnerScreenAdminRelayMime = "";
        if (learnerScreenRemoteAudio && learnerScreenAdminRelayObjectUrl && learnerScreenRemoteAudio.src === learnerScreenAdminRelayObjectUrl) {
          try {
            learnerScreenRemoteAudio.pause();
            learnerScreenRemoteAudio.removeAttribute("src");
            learnerScreenRemoteAudio.load();
          } catch (error) {
          }
        }
        if (learnerScreenAdminRelayObjectUrl) {
          try { URL.revokeObjectURL(learnerScreenAdminRelayObjectUrl); } catch (error) {}
        }
        learnerScreenAdminRelayObjectUrl = "";
      };

      const pumpLearnerScreenAdminRelayBuffer = () => {
        const buffer = learnerScreenAdminRelaySourceBuffer;
        if (!buffer || buffer.updating || !learnerScreenAdminRelayPendingBuffers.length) {
          return;
        }
        try {
          buffer.appendBuffer(learnerScreenAdminRelayPendingBuffers.shift());
        } catch (error) {
          learnerScreenAdminRelayPendingBuffers = [];
        }
      };

      const ensureLearnerScreenAdminRelayBuffer = (mime = "audio/webm;codecs=opus") => {
        if (!SCREEN_AUDIO_RELAY_MEDIA_SOURCE_ENABLED) {
          return false;
        }
        const wantedMime = String(mime || "audio/webm;codecs=opus");
        if (!window.MediaSource || typeof MediaSource.isTypeSupported !== "function" || !MediaSource.isTypeSupported(wantedMime)) {
          return false;
        }
        if (learnerScreenAdminRelayMediaSource && learnerScreenAdminRelayMime === wantedMime && learnerScreenAdminRelaySourceBuffer) {
          return true;
        }
        resetLearnerScreenAdminRelayBuffer();
        learnerScreenAdminRelayMime = wantedMime;
        learnerScreenAdminRelayMediaSource = new MediaSource();
        const audio = ensureLearnerScreenRemoteAudio();
        audio.srcObject = null;
        learnerScreenAdminRelayObjectUrl = URL.createObjectURL(learnerScreenAdminRelayMediaSource);
        audio.src = learnerScreenAdminRelayObjectUrl;
        audio.muted = false;
        audio.volume = 1;
        audio.play().catch(() => {
          setLearnerChatStatus("Admin mic da san sang. Click vao trang neu trinh duyet chan tu dong phat am thanh.");
        });
        learnerScreenAdminRelayMediaSource.addEventListener("sourceopen", () => {
          if (!learnerScreenAdminRelayMediaSource || learnerScreenAdminRelaySourceBuffer) return;
          try {
            learnerScreenAdminRelaySourceBuffer = learnerScreenAdminRelayMediaSource.addSourceBuffer(wantedMime);
            learnerScreenAdminRelaySourceBuffer.mode = "sequence";
            learnerScreenAdminRelaySourceBuffer.addEventListener("updateend", pumpLearnerScreenAdminRelayBuffer);
            pumpLearnerScreenAdminRelayBuffer();
          } catch (error) {
            resetLearnerScreenAdminRelayBuffer();
          }
        }, { once: true });
        return true;
      };

      const stopLearnerScreenAdminAudioPolling = () => {
        if (learnerScreenAdminAudioPollTimer) {
          window.clearTimeout(learnerScreenAdminAudioPollTimer);
          learnerScreenAdminAudioPollTimer = 0;
        }
        learnerScreenAdminAudioPolling = false;
        learnerScreenAdminAudioLastChunkId = 0;
        learnerScreenAdminAudioQueue = [];
        learnerScreenAdminAudioPlaying = false;
        if (learnerScreenAdminAudioCurrent) {
          try {
            learnerScreenAdminAudioCurrent.pause();
            learnerScreenAdminAudioCurrent.src = "";
          } catch (error) {
          }
        }
        learnerScreenAdminAudioCurrent = null;
        resetLearnerScreenAdminRelayBuffer();
        if (learnerScreenRemoteAudio) {
          learnerScreenRemoteAudio.srcObject = null;
        }
      };

      const playLearnerScreenAdminAudioQueue = () => {
        if (learnerScreenAdminAudioPlaying || !learnerScreenAdminAudioQueue.length || learnerScreenAdminWebRtcAudioLive()) {
          return;
        }
        const chunk = learnerScreenAdminAudioQueue.shift();
        if (!chunk || !chunk.data) {
          window.setTimeout(playLearnerScreenAdminAudioQueue, 0);
          return;
        }
        learnerScreenAdminAudioPlaying = true;
        const audio = new Audio(String(chunk.data || ""));
        learnerScreenAdminAudioCurrent = audio;
        const finish = () => {
          if (learnerScreenAdminAudioCurrent === audio) {
            learnerScreenAdminAudioCurrent = null;
          }
          learnerScreenAdminAudioPlaying = false;
          window.setTimeout(playLearnerScreenAdminAudioQueue, 0);
        };
        audio.addEventListener("ended", finish, { once: true });
        audio.addEventListener("error", finish, { once: true });
        audio.play().catch(() => {
          setLearnerChatStatus("Admin mic da san sang. Click vao trang neu trinh duyet chan tu dong phat am thanh.");
          finish();
        });
      };

      const queueLearnerScreenAdminAudioChunk = (chunk = {}) => {
        if (!chunk || !chunk.data || learnerScreenAdminWebRtcAudioLive()) {
          return;
        }
        const mime = screenMimeFromDataUrl(chunk.data, chunk.mime || "audio/webm;codecs=opus");
        const bytes = screenDataUrlToBytes(chunk.data);
        if (bytes && ensureLearnerScreenAdminRelayBuffer(mime)) {
          learnerScreenAdminRelayPendingBuffers.push(bytes);
          if (learnerScreenAdminRelayPendingBuffers.length > 18) {
            learnerScreenAdminRelayPendingBuffers.splice(0, learnerScreenAdminRelayPendingBuffers.length - 12);
          }
          pumpLearnerScreenAdminRelayBuffer();
          return;
        }
        learnerScreenAdminAudioQueue.push(chunk);
        if (learnerScreenAdminAudioQueue.length > 5) {
          learnerScreenAdminAudioQueue = learnerScreenAdminAudioQueue.slice(-5);
        }
        playLearnerScreenAdminAudioQueue();
      };

      const scheduleLearnerScreenAdminAudioPolling = (delayMs = ADMIN_SCREEN_AUDIO_POLL_MS) => {
        if (learnerScreenAdminAudioPollTimer) {
          window.clearTimeout(learnerScreenAdminAudioPollTimer);
          learnerScreenAdminAudioPollTimer = 0;
        }
        if (!authToken || !learnerScreenSession || learnerScreenSession.state !== "active") {
          return;
        }
        learnerScreenAdminAudioPollTimer = window.setTimeout(() => void pollLearnerScreenAdminAudioChunks(), Math.max(90, Number(delayMs) || ADMIN_SCREEN_AUDIO_POLL_MS));
      };

      const pollLearnerScreenAdminAudioChunks = async () => {
        if (learnerScreenAdminAudioPolling || !authToken || !learnerScreenSession || learnerScreenSession.state !== "active") {
          return;
        }
        if (learnerScreenAdminWebRtcAudioLive()) {
          learnerScreenAdminAudioQueue = [];
          scheduleLearnerScreenAdminAudioPolling(900);
          return;
        }
        learnerScreenAdminAudioPolling = true;
        try {
          const { payload } = await fetchAuthJson(`/screen/audio?session=${encodeURIComponent(learnerScreenSession.id)}&after=${encodeURIComponent(String(learnerScreenAdminAudioLastChunkId || 0))}`);
          if (payload.session && payload.session.id) {
            learnerScreenSession = payload.session;
          }
          const chunks = Array.isArray(payload.chunks) ? payload.chunks : [];
          chunks.forEach((chunk) => {
            learnerScreenAdminAudioLastChunkId = Math.max(learnerScreenAdminAudioLastChunkId, Number(chunk.id || 0));
          });
          chunks.slice(-3).forEach(queueLearnerScreenAdminAudioChunk);
        } catch (error) {
        } finally {
          learnerScreenAdminAudioPolling = false;
          scheduleLearnerScreenAdminAudioPolling(ADMIN_SCREEN_AUDIO_POLL_MS);
        }
      };

      const startLearnerScreenAdminAudioPolling = () => {
        if (!authToken || !learnerScreenSession || learnerScreenSession.state !== "active") {
          return;
        }
        scheduleLearnerScreenAdminAudioPolling(0);
      };

      const startLearnerScreenWebRtc = async () => {
        if (!LEARNER_SCREEN_WEBRTC_ENABLED) {
          return;
        }
        if (!learnerScreenSession || learnerScreenSession.state !== "active" || !learnerScreenCaptureStream || learnerScreenPeer) {
          return;
        }
        if (!window.RTCPeerConnection) {
          setLearnerChatStatus("Trinh duyet khong ho tro WebRTC screen.", "error");
          return;
        }
        if (typeof refreshServerSettings === "function") {
          await refreshServerSettings();
        }
        if (!webRtcHasTurnRelay()) {
          setLearnerChatStatus("Screen dang bat. Neu khac mang, server relay se ho tro khi WebRTC direct bi chan.");
        }
        learnerScreenPeer = new RTCPeerConnection(webRtcConfig);
        learnerScreenPeer.addEventListener("datachannel", (event) => {
          if (event.channel && event.channel.label === "screen-control") {
            attachLearnerScreenControlChannel(event.channel);
          }
        });
        learnerScreenPeer.addEventListener("track", (event) => {
          if (event.track && event.track.kind === "audio") {
            const audio = ensureLearnerScreenRemoteAudio();
            audio.srcObject = event.streams && event.streams[0] ? event.streams[0] : new MediaStream([event.track]);
            audio.play().catch(() => {
              setLearnerChatStatus("Admin mic direct da san sang. Click vao trang neu trinh duyet chan am thanh.");
            });
          }
        });
        learnerScreenCaptureStream.getVideoTracks().forEach((track) => {
          const sender = learnerScreenPeer.addTrack(track, learnerScreenCaptureStream);
          if (sender && typeof sender.getParameters === "function" && typeof sender.setParameters === "function") {
            try {
              const params = sender.getParameters() || {};
              params.degradationPreference = "maintain-resolution";
              params.encodings = Array.isArray(params.encodings) && params.encodings.length ? params.encodings : [{}];
              const settings = track && typeof track.getSettings === "function" ? track.getSettings() : {};
              const sourceWidth = Math.max(1, Number(settings.width || LEARNER_SCREEN_WEBRTC_WIDTH) || LEARNER_SCREEN_WEBRTC_WIDTH);
              const sourceHeight = Math.max(1, Number(settings.height || LEARNER_SCREEN_WEBRTC_HEIGHT) || LEARNER_SCREEN_WEBRTC_HEIGHT);
              const downscale = Math.max(1, sourceWidth / LEARNER_SCREEN_WEBRTC_WIDTH, sourceHeight / LEARNER_SCREEN_WEBRTC_HEIGHT);
              params.encodings[0] = {
                ...params.encodings[0],
                maxBitrate: LEARNER_SCREEN_WEBRTC_BITRATE,
                maxFramerate: LEARNER_SCREEN_WEBRTC_FRAMERATE,
                scaleResolutionDownBy: Number(downscale.toFixed(2)),
              };
              void sender.setParameters(params).catch(() => {});
            } catch (error) {
            }
          }
        });
        learnerScreenCaptureStream.getAudioTracks().forEach((track) => {
          try {
            learnerScreenPeer.addTrack(track, learnerScreenCaptureStream);
          } catch (error) {
          }
        });
        if (learnerScreenMicStream) {
          screenAudioTracks(learnerScreenMicStream).forEach((track) => {
            try {
              learnerScreenPeer.addTrack(track, learnerScreenMicStream);
            } catch (error) {
            }
          });
        }
        learnerScreenPeer.addEventListener("icecandidate", (event) => {
          if (event.candidate) {
            void sendLearnerScreenWebRtcSignal("candidate", event.candidate.toJSON());
          }
        });
        learnerScreenPeer.addEventListener("connectionstatechange", () => {
          if (!learnerScreenPeer) return;
          setLearnerChatStatus(`Screen WebRTC: ${learnerScreenPeer.connectionState}`);
        });
      };

      const pollLearnerScreenWebRtcSignals = async () => {
        if (!learnerScreenSession || learnerScreenSession.state !== "active" || !learnerScreenPeer) {
          return;
        }
        const result = await fetchAuthJson(`/screen/signal?session=${encodeURIComponent(learnerScreenSession.id)}&after=${encodeURIComponent(String(learnerScreenRemoteCandidateId))}`);
        const payload = result.payload || {};
        if (payload.session && payload.session.state && payload.session.state !== "active") {
          handleLearnerScreenSession(payload.session);
          return;
        }
        const offerKey = payload.offer ? `${payload.offer.type || ""}:${payload.offer.sdp || ""}` : "";
        if (payload.offer && offerKey && offerKey !== learnerScreenOfferKey) {
          if (learnerScreenPeer && learnerScreenOfferKey) {
            resetLearnerScreenPeer();
            await startLearnerScreenWebRtc();
          }
          if (!learnerScreenPeer) {
            await startLearnerScreenWebRtc();
          }
          if (!learnerScreenPeer) {
            return;
          }
          await learnerScreenPeer.setRemoteDescription(new RTCSessionDescription(payload.offer));
          learnerScreenOfferSet = true;
          learnerScreenOfferKey = offerKey;
          const answer = await learnerScreenPeer.createAnswer();
          await learnerScreenPeer.setLocalDescription(answer);
          await sendLearnerScreenWebRtcSignal("answer", learnerScreenPeer.localDescription.toJSON());
          learnerScreenAnswerSent = true;
        }
        const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
        for (const item of candidates) {
          if (item.candidate && learnerScreenOfferSet) {
            learnerScreenRemoteCandidateId = Math.max(learnerScreenRemoteCandidateId, Number(item.id || 0));
            try {
              await learnerScreenPeer.addIceCandidate(new RTCIceCandidate(item.candidate));
            } catch (error) {
            }
          }
        }
      };

      const sendLearnerScreenFrame = async () => {
        const frameClock = () => (typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now());
        if (
          learnerScreenSending
          || !authToken
          || !learnerScreenSession
          || learnerScreenSession.state !== "active"
          || !learnerScreenCaptureStream
        ) {
          return;
        }
        const track = learnerScreenCaptureStream.getVideoTracks()[0];
        if (!track || track.readyState === "ended") {
          return;
        }
        const { video, canvas } = ensureLearnerScreenNodes();
        const sourceWidth = Number(video.videoWidth || track.getSettings && track.getSettings().width || 0);
        const sourceHeight = Number(video.videoHeight || track.getSettings && track.getSettings().height || 0);
        if (!sourceWidth || !sourceHeight) {
          return;
        }
        const scale = Math.min(
          1,
          LEARNER_SCREEN_PREVIEW_MAX_WIDTH / Math.max(sourceWidth, 1),
          LEARNER_SCREEN_PREVIEW_MAX_HEIGHT / Math.max(sourceHeight, 1),
        );
        const width = Math.max(1, Math.round(sourceWidth * scale));
        const height = Math.max(1, Math.round(sourceHeight * scale));
        learnerScreenSending = true;
        const frameStartedAt = frameClock();
        try {
          if (canvas.width !== width) {
            canvas.width = width;
          }
          if (canvas.height !== height) {
            canvas.height = height;
          }
          const context = canvas.getContext("2d");
          if (!context) {
            return;
          }
          context.drawImage(video, 0, 0, width, height);
          const encodeStartedAt = frameClock();
          const blob = await canvasToLearnerScreenBlob(canvas, LEARNER_SCREEN_PREVIEW_QUALITY);
          const encodeMs = Math.max(0, frameClock() - encodeStartedAt);
          let result = null;
          let uploadMs = 0;
          let bytes = blob && Number(blob.size || 0) || 0;
          let mode = "";
          if (LEARNER_SCREEN_PREVIEW_BINARY_ENABLED && learnerScreenBinaryFrameEnabled && blob) {
            const params = new URLSearchParams({
              session: learnerScreenSession.id,
              width: String(width),
              height: String(height),
              mime: blob.type || LEARNER_SCREEN_PREVIEW_MIME,
              encode_ms: String(Math.round(encodeMs)),
            });
            const uploadStartedAt = frameClock();
            try {
              result = await fetchAuthJson(`/screen/frame-binary?${params.toString()}`, {
                method: "POST",
                headers: { "Content-Type": blob.type || LEARNER_SCREEN_PREVIEW_MIME },
                body: blob,
                timeoutMs: 5000,
              });
              uploadMs = Math.max(0, frameClock() - uploadStartedAt);
              mode = "binary";
            } catch (error) {
              learnerScreenBinaryFrameEnabled = false;
            }
          }
          if (!result) {
            const data = blob ? await blobToLearnerScreenDataUrl(blob) : await canvasToLearnerScreenJpeg(canvas, LEARNER_SCREEN_PREVIEW_QUALITY);
            if (!data) {
              return;
            }
            bytes = data.length;
            const uploadStartedAt = frameClock();
            result = await fetchAuthJson("/screen/frame", {
              method: "POST",
              body: JSON.stringify({
                session: learnerScreenSession.id,
                data,
                width,
                height,
                encode_ms: Math.round(encodeMs),
              }),
              timeoutMs: 5000,
            });
            uploadMs = Math.max(0, frameClock() - uploadStartedAt);
            mode = "json";
          }
          learnerScreenFrameLastElapsedMs = Math.max(0, frameClock() - frameStartedAt);
          learnerScreenFrameLastEncodeMs = encodeMs;
          learnerScreenFrameLastUploadMs = uploadMs;
          learnerScreenFrameLastBytes = bytes;
          learnerScreenFrameLastMode = mode;
          if (result.payload && result.payload.session) {
            handleLearnerScreenSession(result.payload.session);
          }
        } catch (error) {
        } finally {
          learnerScreenSending = false;
        }
      };

      const startLearnerScreenCapture = async (options = {}) => {
        if (!authToken) {
          showLoginGate("Sign in to share your screen.");
          return;
        }
        if (learnerScreenCaptureStarting) {
          return;
        }
        const currentState = learnerScreenSession && learnerScreenSession.state || "";
        if (learnerScreenSession && !["pending_user", "active"].includes(currentState)) {
          setLearnerChatStatus("Screen session chua san sang.");
          return;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
          setLearnerChatStatus("Trinh duyet khong ho tro chia se man hinh.", "error");
          return;
        }
        learnerScreenCaptureStarting = true;
        try {
          const stream = await navigator.mediaDevices.getDisplayMedia(learnerScreenCaptureOptions());
          stopLearnerScreenCapture();
          learnerScreenCaptureStarting = true;
          learnerScreenCaptureStream = stream;
          requestLearnerScreenFullscreen();
          window.setTimeout(requestLearnerScreenFullscreen, 350);
          const { video } = ensureLearnerScreenNodes();
          video.srcObject = stream;
          await video.play();
          const track = stream.getVideoTracks()[0];
          if (track) {
            track.addEventListener("ended", () => {
              void endLearnerScreenSession();
            }, { once: true });
          }
          const requested = await fetchAuthJson("/screen/request", { method: "POST", body: JSON.stringify({}) });
          handleLearnerScreenSession(requested.payload && requested.payload.session || {});
          if (learnerScreenSession && learnerScreenSession.state === "pending_user") {
            const result = await fetchAuthJson("/screen/action", {
              method: "POST",
              body: JSON.stringify({ session: learnerScreenSession.id, action: "accept" }),
            });
            handleLearnerScreenSession(result.payload && result.payload.session || {});
          }
          void startLearnerScreenAudioRelay();
          scheduleLearnerScreenMicRelayUpgrade();
          await startLearnerScreenWebRtc();
          await pollLearnerScreenWebRtcSignals();
          if (learnerScreenFrameTimer) {
            window.clearTimeout(learnerScreenFrameTimer);
            learnerScreenFrameTimer = 0;
          }
          scheduleLearnerScreenFrameLoop(80);
        } catch (error) {
          stopLearnerScreenCapture();
          const message = error && error.message ? error.message : "Khong mo duoc chia se man hinh.";
          setLearnerChatStatus(options.autoPrompt ? `${message} Bam nut Screen tren may user de mo hop chon lai.` : message, "error");
        } finally {
          learnerScreenCaptureStarting = false;
        }
      };

      const pollLearnerScreen = async () => {
        if (!authToken || learnerScreenPollInFlight) {
          return;
        }
        learnerScreenPollInFlight = true;
        try {
          const state = await fetchAuthJson("/screen/state");
          handleLearnerScreenSession(state.payload && state.payload.session || {});
          if (learnerScreenSession && learnerScreenSession.state === "active" && learnerScreenPeer) {
            await pollLearnerScreenWebRtcSignals();
          }
        } catch (error) {
        } finally {
          learnerScreenPollInFlight = false;
        }
      };

      // Added 2026-07-01: keeps screen polling disabled until the learner starts/accepts screen sharing.
      const shouldKeepLearnerScreenPolling = () => {
        const state = learnerScreenSession && learnerScreenSession.state || "";
        return Boolean(authToken && state && ["active", "pending_user", "pending_admin"].includes(state));
      };

      const learnerScreenPollDelay = () => {
        const state = learnerScreenSession && learnerScreenSession.state || "";
        const base = ["active", "pending_user", "pending_admin"].includes(state)
          ? LEARNER_SCREEN_POLL_ACTIVE_MS
          : LEARNER_SCREEN_POLL_IDLE_MS;
        return state ? base : serverWorkspacePollDelay(base);
      };

      const scheduleLearnerScreenPolling = (delayMs = learnerScreenPollDelay()) => {
        if (learnerScreenPollTimer) {
          window.clearTimeout(learnerScreenPollTimer);
          learnerScreenPollTimer = 0;
        }
        if (!authToken) {
          return;
        }
        if (!shouldKeepLearnerScreenPolling()) {
          return;
        }
        learnerScreenPollTimer = window.setTimeout(async () => {
          learnerScreenPollTimer = 0;
          await pollLearnerScreen();
          scheduleLearnerScreenPolling();
        }, Math.max(700, Number(delayMs) || learnerScreenPollDelay()));
      };

      const startLearnerScreenPolling = () => {
        if (learnerScreenPollTimer) {
          window.clearTimeout(learnerScreenPollTimer);
          learnerScreenPollTimer = 0;
        }
        if (!authToken) {
          return;
        }
        void pollLearnerScreen().finally(() => {
          if (shouldKeepLearnerScreenPolling()) {
            scheduleLearnerScreenPolling();
          }
        });
      };

      const stopLearnerScreenPolling = () => {
        if (learnerScreenPollTimer) {
          window.clearTimeout(learnerScreenPollTimer);
          learnerScreenPollTimer = 0;
        }
        learnerScreenPollInFlight = false;
        stopLearnerScreenCapture();
        learnerScreenSession = null;
        updateLearnerScreenUi();
      };

      const requestOrAcceptLearnerScreen = async () => {
        if (!authToken) {
          showLoginGate("Sign in to share your screen.");
          return;
        }
        if (learnerScreenSession && learnerScreenSession.state === "active" && learnerScreenCaptureStream) {
          await endLearnerScreenSession();
          setLearnerChatStatus("Da dung chia se man hinh.");
          return;
        }
        await startLearnerScreenCapture();
        startLearnerScreenPolling();
      };

      const setAdminScreenStatus = (message = "", tone = "") => {
        if (!adminScreenStatus) {
          return;
        }
        adminScreenStatus.textContent = message || "Ready";
        adminScreenStatus.classList.toggle("is-error", tone === "error");
        adminScreenStatus.classList.toggle("is-ok", tone === "ok");
      };

      const setAdminScreenPlaceholder = (message = "", hidden = false) => {
        if (!adminScreenPlaceholder) {
          return;
        }
        adminScreenPlaceholder.hidden = Boolean(hidden);
        if (message || !hidden) {
          adminScreenPlaceholder.textContent = message || "Waiting for screen...";
        }
      };

      const ensureAdminScreenRemoteAudio = () => {
        if (!adminScreenRemoteAudio) {
          adminScreenRemoteAudio = document.createElement("audio");
          adminScreenRemoteAudio.autoplay = true;
          adminScreenRemoteAudio.playsInline = true;
          adminScreenRemoteAudio.style.display = "none";
          document.body.appendChild(adminScreenRemoteAudio);
        }
        return adminScreenRemoteAudio;
      };

      const adminScreenWebRtcAudioLive = () => Boolean(
        adminScreenRemoteAudio
        && adminScreenRemoteAudio.srcObject
        && adminScreenRemoteAudio.srcObject.getAudioTracks
        && adminScreenRemoteAudio.srcObject.getAudioTracks().some((track) => track.readyState !== "ended"),
      );

      const screenDataUrlToBytes = (dataUrl = "") => {
        const raw = String(dataUrl || "");
        const comma = raw.indexOf(",");
        if (comma < 0) return null;
        try {
          const binary = atob(raw.slice(comma + 1));
          const bytes = new Uint8Array(binary.length);
          for (let index = 0; index < binary.length; index += 1) {
            bytes[index] = binary.charCodeAt(index);
          }
          return bytes;
        } catch (error) {
          return null;
        }
      };

      const screenMimeFromDataUrl = (dataUrl = "", fallback = "audio/webm;codecs=opus") => {
        const match = String(dataUrl || "").match(/^data:([^;,]+(?:;codecs=[^;,]+)?)/i);
        return match && match[1] ? match[1] : fallback;
      };

      const resetAdminScreenRelayBuffer = () => {
        adminScreenRelayPendingBuffers = [];
        adminScreenRelaySourceBuffer = null;
        if (adminScreenRelayMediaSource) {
          try {
            if (adminScreenRelayMediaSource.readyState === "open") {
              adminScreenRelayMediaSource.endOfStream();
            }
          } catch (error) {
          }
        }
        adminScreenRelayMediaSource = null;
        adminScreenRelayMime = "";
        if (adminScreenRemoteAudio && adminScreenRelayObjectUrl && adminScreenRemoteAudio.src === adminScreenRelayObjectUrl) {
          try {
            adminScreenRemoteAudio.pause();
            adminScreenRemoteAudio.removeAttribute("src");
            adminScreenRemoteAudio.load();
          } catch (error) {
          }
        }
        if (adminScreenRelayObjectUrl) {
          try { URL.revokeObjectURL(adminScreenRelayObjectUrl); } catch (error) {}
        }
        adminScreenRelayObjectUrl = "";
      };

      const pumpAdminScreenRelayBuffer = () => {
        const buffer = adminScreenRelaySourceBuffer;
        if (!buffer || buffer.updating || !adminScreenRelayPendingBuffers.length) {
          return;
        }
        try {
          buffer.appendBuffer(adminScreenRelayPendingBuffers.shift());
        } catch (error) {
          adminScreenAudioDropped += Math.max(1, adminScreenRelayPendingBuffers.length);
          adminScreenRelayPendingBuffers = [];
        }
      };

      const ensureAdminScreenRelayBuffer = (mime = "audio/webm;codecs=opus") => {
        if (!SCREEN_AUDIO_RELAY_MEDIA_SOURCE_ENABLED) {
          return false;
        }
        const wantedMime = String(mime || "audio/webm;codecs=opus");
        if (!window.MediaSource || typeof MediaSource.isTypeSupported !== "function" || !MediaSource.isTypeSupported(wantedMime)) {
          return false;
        }
        if (adminScreenRelayMediaSource && adminScreenRelayMime === wantedMime && adminScreenRelaySourceBuffer) {
          return true;
        }
        resetAdminScreenRelayBuffer();
        adminScreenRelayMime = wantedMime;
        adminScreenRelayMediaSource = new MediaSource();
        const audio = ensureAdminScreenRemoteAudio();
        audio.srcObject = null;
        adminScreenRelayObjectUrl = URL.createObjectURL(adminScreenRelayMediaSource);
        audio.src = adminScreenRelayObjectUrl;
        audio.muted = false;
        audio.volume = 1;
        audio.play().catch(() => {
          setAdminScreenStatus("Screen audio relay is ready. Click inside the screen panel if the browser blocks autoplay.");
        });
        adminScreenRelayMediaSource.addEventListener("sourceopen", () => {
          if (!adminScreenRelayMediaSource || adminScreenRelaySourceBuffer) return;
          try {
            adminScreenRelaySourceBuffer = adminScreenRelayMediaSource.addSourceBuffer(wantedMime);
            adminScreenRelaySourceBuffer.mode = "sequence";
            adminScreenRelaySourceBuffer.addEventListener("updateend", pumpAdminScreenRelayBuffer);
            pumpAdminScreenRelayBuffer();
          } catch (error) {
            resetAdminScreenRelayBuffer();
          }
        }, { once: true });
        return true;
      };

      const stopAdminScreenCurrentAudio = () => {
        resetAdminScreenRelayBuffer();
        if (adminScreenCurrentAudio) {
          try {
            adminScreenCurrentAudio.pause();
            adminScreenCurrentAudio.src = "";
          } catch (error) {
          }
        }
        adminScreenCurrentAudio = null;
        adminScreenAudioPlaying = false;
      };

      const stopAdminScreenAudioRelay = () => {
        if (adminScreenAudioPollTimer) {
          window.clearTimeout(adminScreenAudioPollTimer);
          adminScreenAudioPollTimer = 0;
        }
        adminScreenAudioPolling = false;
        adminScreenAudioQueue = [];
        adminScreenAudioLastChunkId = 0;
        adminScreenAudioDropped = 0;
        stopAdminScreenCurrentAudio();
        if (adminScreenRemoteAudio) {
          adminScreenRemoteAudio.srcObject = null;
        }
      };

      const playAdminScreenAudioQueue = () => {
        if (adminScreenAudioPlaying || !adminScreenAudioQueue.length || adminScreenWebRtcAudioLive()) {
          return;
        }
        const chunk = adminScreenAudioQueue.shift();
        if (!chunk || !chunk.data) {
          window.setTimeout(playAdminScreenAudioQueue, 0);
          return;
        }
        adminScreenAudioPlaying = true;
        const audio = new Audio(String(chunk.data || ""));
        adminScreenCurrentAudio = audio;
        const finish = () => {
          if (adminScreenCurrentAudio === audio) {
            adminScreenCurrentAudio = null;
          }
          adminScreenAudioPlaying = false;
          window.setTimeout(playAdminScreenAudioQueue, 0);
        };
        audio.addEventListener("ended", finish, { once: true });
        audio.addEventListener("error", finish, { once: true });
        audio.play().catch(() => {
          setAdminScreenStatus("Screen audio relay is ready. Click inside the screen panel if the browser blocks autoplay.");
          finish();
        });
      };

      const queueAdminScreenAudioChunk = (chunk = {}) => {
        if (!chunk || !chunk.data || adminScreenWebRtcAudioLive()) {
          return;
        }
        const mime = screenMimeFromDataUrl(chunk.data, chunk.mime || "audio/webm;codecs=opus");
        const bytes = screenDataUrlToBytes(chunk.data);
        if (bytes && ensureAdminScreenRelayBuffer(mime)) {
          adminScreenRelayPendingBuffers.push(bytes);
          if (adminScreenRelayPendingBuffers.length > 18) {
            const dropCount = adminScreenRelayPendingBuffers.length - 12;
            adminScreenRelayPendingBuffers.splice(0, dropCount);
            adminScreenAudioDropped += dropCount;
          }
          pumpAdminScreenRelayBuffer();
          return;
        }
        adminScreenAudioQueue.push(chunk);
        if (adminScreenAudioQueue.length > 5) {
          adminScreenAudioDropped += adminScreenAudioQueue.length - 5;
          adminScreenAudioQueue = adminScreenAudioQueue.slice(-5);
        }
        playAdminScreenAudioQueue();
      };

      const scheduleAdminScreenAudioPolling = (delayMs = ADMIN_SCREEN_AUDIO_POLL_MS) => {
        if (adminScreenAudioPollTimer) {
          window.clearTimeout(adminScreenAudioPollTimer);
          adminScreenAudioPollTimer = 0;
        }
        if (!adminScreenOpen || !adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active") {
          return;
        }
        adminScreenAudioPollTimer = window.setTimeout(() => void pollAdminScreenAudioChunks(), Math.max(80, Number(delayMs) || ADMIN_SCREEN_AUDIO_POLL_MS));
      };

      const pollAdminScreenAudioChunks = async () => {
        if (adminScreenAudioPolling || !adminScreenOpen || !adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active") {
          return;
        }
        if (adminScreenWebRtcAudioLive()) {
          adminScreenAudioQueue = [];
          stopAdminScreenCurrentAudio();
          scheduleAdminScreenAudioPolling(900);
          return;
        }
        adminScreenAudioPolling = true;
        try {
          const { payload } = await fetchAuthJson(`/screen/auth-admin/audio?username=${encodeURIComponent(adminScreenUser)}&session=${encodeURIComponent(adminScreenSession.id)}&after=${encodeURIComponent(String(adminScreenAudioLastChunkId || 0))}`);
          if (payload.session && payload.session.id) {
            adminScreenSession = payload.session;
          }
          const chunks = Array.isArray(payload.chunks) ? payload.chunks : [];
          chunks.forEach((chunk) => {
            adminScreenAudioLastChunkId = Math.max(adminScreenAudioLastChunkId, Number(chunk.id || 0));
          });
          const playable = chunks.slice(-3);
          adminScreenAudioDropped += Math.max(0, chunks.length - playable.length);
          playable.forEach(queueAdminScreenAudioChunk);
        } catch (error) {
        } finally {
          adminScreenAudioPolling = false;
          scheduleAdminScreenAudioPolling(ADMIN_SCREEN_AUDIO_POLL_MS);
        }
      };

      const adminScreenIceUrls = () => normalizeWebRtcIceServers(webRtcConfig.iceServers).flatMap((server) => server.urls || []);

      const adminScreenTransportSnapshot = (event = "manual-check") => {
        const videoLive = adminScreenWebRtcVideoLive();
        const frameLive = Boolean(adminScreenImg && adminScreenImg.getAttribute("src"));
        return {
          event,
          mode: adminScreenTransportPreference,
          username: adminScreenUser || "",
          session: adminScreenSession && adminScreenSession.id || "",
          transport: videoLive ? "webrtc-video" : (frameLive ? "server-relay-frame" : "pending"),
          control: adminScreenControlChannelOpen() ? "webrtc-datachannel" : "http-control",
          peer_state: adminScreenPeer && (adminScreenPeer.connectionState || "") || "",
          ice_state: adminScreenPeer && (adminScreenPeer.iceConnectionState || "") || "",
          data_channel: adminScreenControlChannel && adminScreenControlChannel.readyState || "",
          frame_id: adminScreenFrameId || 0,
          relay_fps: Number(adminScreenRelayFps || 0).toFixed(2),
          relay_frame_chars: adminScreenRelayFrameChars || 0,
          relay_frame_width: adminScreenRelayFrameWidth || 0,
          relay_frame_height: adminScreenRelayFrameHeight || 0,
          audio: adminScreenWebRtcAudioLive() ? "webrtc-audio" : (adminScreenAudioLastChunkId ? "relay-audio" : "pending"),
          admin_mic: adminScreenMicEnabled ? (adminScreenMicSending ? "relay-sending" : "enabled") : "off",
          audio_chunk_id: adminScreenAudioLastChunkId || 0,
          audio_queue: adminScreenAudioQueue.length || 0,
          audio_dropped: adminScreenAudioDropped || 0,
          has_turn: webRtcHasTurnRelay(),
          force_relay: webRtcConfig.iceTransportPolicy === "relay",
          ice_urls: adminScreenIceUrls(),
        };
      };

      const renderAdminScreenTransportLog = () => {
        if (!adminScreenLog) {
          return;
        }
        adminScreenLog.textContent = "";
        adminScreenTransportLogRows.slice(-8).forEach((row) => {
          const item = document.createElement("span");
          item.className = "ft-admin-screen-log-entry";
          item.textContent = row;
          adminScreenLog.appendChild(item);
        });
      };

      const ADMIN_SCREEN_TRANSPORT_MODE_KEY = "future_admin_screen_transport_mode";
      const adminScreenTransportModeLabel = (mode = adminScreenTransportPreference) => {
        if (mode === "realtime") return "Realtime";
        if (mode === "relay") return "Relay";
        return "Auto";
      };
      const normalizeAdminScreenTransportPreference = (mode = "") => {
        const value = clean(mode).toLowerCase();
        return ["auto", "realtime", "relay"].includes(value) ? value : "auto";
      };
      const updateAdminScreenModeButton = () => {
        if (!adminScreenModeButton) {
          return;
        }
        adminScreenModeButton.textContent = `Mode: ${adminScreenTransportModeLabel()}`;
        adminScreenModeButton.title = adminScreenTransportPreference === "relay"
          ? "Relay: server frame fallback only."
          : adminScreenTransportPreference === "realtime"
            ? "Realtime: prefer WebRTC direct/TURN video."
            : "Auto: WebRTC first, server relay fallback.";
      };
      const loadAdminScreenTransportPreference = () => {
        try {
          adminScreenTransportPreference = normalizeAdminScreenTransportPreference(localStorage.getItem(ADMIN_SCREEN_TRANSPORT_MODE_KEY) || "auto");
        } catch (error) {
          adminScreenTransportPreference = "auto";
        }
        updateAdminScreenModeButton();
      };
      const setAdminScreenTransportPreference = (mode = "auto", reconnect = false) => {
        adminScreenTransportPreference = normalizeAdminScreenTransportPreference(mode);
        try {
          localStorage.setItem(ADMIN_SCREEN_TRANSPORT_MODE_KEY, adminScreenTransportPreference);
        } catch (error) {
        }
        updateAdminScreenModeButton();
        void writeAdminScreenTransportLog(`mode-${adminScreenTransportPreference}`, true);
        if (reconnect && adminScreenOpen && adminScreenSession && adminScreenSession.state === "active") {
          void reconnectAdminScreen();
        }
      };
      const cycleAdminScreenTransportPreference = () => {
        const next = adminScreenTransportPreference === "auto"
          ? "realtime"
          : adminScreenTransportPreference === "realtime"
            ? "relay"
            : "auto";
        setAdminScreenTransportPreference(next, true);
      };

      const writeAdminScreenTransportLog = async (event = "manual-check", force = false) => {
        const snapshot = adminScreenTransportSnapshot(event);
        const timeLabel = new Date().toLocaleTimeString();
        const relaySizeLabel = snapshot.relay_frame_width && snapshot.relay_frame_height
          ? `${snapshot.relay_frame_width}x${snapshot.relay_frame_height}`
          : "-";
        const line = `${timeLabel} | ${adminScreenTransportModeLabel(snapshot.mode)} | ${snapshot.transport} | ${snapshot.control} | audio:${snapshot.audio || "-"}#${snapshot.audio_chunk_id || 0} | fps:${snapshot.relay_fps || "0.00"} | ${relaySizeLabel} | chars:${snapshot.relay_frame_chars || 0} | peer:${snapshot.peer_state || "-"} ice:${snapshot.ice_state || "-"} frame:${snapshot.frame_id}`;
        adminScreenTransportLogRows.push(line);
        adminScreenTransportLogRows = adminScreenTransportLogRows.slice(-20);
        renderAdminScreenTransportLog();
        if (!force && !snapshot.username) {
          return;
        }
        try {
          await fetchAuthJson("/screen/auth-admin/transport-log", {
            method: "POST",
            body: JSON.stringify(snapshot),
          });
        } catch (error) {
        }
      };

      const setAdminScreenTransportMode = (mode = "", event = "") => {
        const nextMode = clean(mode);
        if (!nextMode || nextMode === adminScreenTransportMode) {
          return;
        }
        adminScreenTransportMode = nextMode;
        void writeAdminScreenTransportLog(event || nextMode);
      };

      const adminScreenWebRtcVideoLive = () => Boolean(
        adminScreenVideo
        && adminScreenVideo.srcObject
        && adminScreenVideo.style.display !== "none"
        && (Number(adminScreenVideo.videoWidth || 0) > 0 || Number(adminScreenVideo.readyState || 0) >= 2),
      );

      const adminScreenControlChannelOpen = () => Boolean(adminScreenControlChannel && adminScreenControlChannel.readyState === "open");

      const resetAdminScreenTransport = () => {
        if (adminScreenPollTimer) {
          window.clearTimeout(adminScreenPollTimer);
          adminScreenPollTimer = 0;
        }
        if (adminScreenFrameTimer) {
          window.clearTimeout(adminScreenFrameTimer);
          adminScreenFrameTimer = 0;
        }
        if (adminScreenControlTimer) {
          window.clearTimeout(adminScreenControlTimer);
          adminScreenControlTimer = 0;
        }
        stopAdminScreenAudioRelay();
        adminScreenControlQueue = [];
        adminScreenControlSending = false;
        if (adminScreenControlChannel) {
          try { adminScreenControlChannel.close(); } catch (error) {}
        }
        adminScreenControlChannel = null;
        adminScreenPointerActive = false;
        adminScreenTransportMode = "";
        if (adminScreenPeer) {
          try { adminScreenPeer.close(); } catch (error) {}
        }
        adminScreenPeer = null;
        adminScreenRemoteCandidateId = 0;
        adminScreenOfferSent = false;
        adminScreenAnswerSet = false;
        adminScreenFrameId = 0;
        adminScreenRelayLastFrameAt = 0;
        adminScreenRelayLastFrameId = 0;
        adminScreenRelayFps = 0;
        adminScreenRelayFrameChars = 0;
        adminScreenRelayFrameWidth = 0;
        adminScreenRelayFrameHeight = 0;
        if (adminScreenVideo) {
          adminScreenVideo.srcObject = null;
          adminScreenVideo.style.display = "none";
        }
        if (adminScreenImg) {
          adminScreenImg.removeAttribute("src");
          adminScreenImg.style.display = "";
        }
      };

      const adminScreenActiveMedia = () => {
        if (adminScreenVideo && adminScreenVideo.srcObject && adminScreenVideo.videoWidth && adminScreenVideo.videoHeight && adminScreenVideo.style.display !== "none") {
          return adminScreenVideo;
        }
        if (adminScreenImg && adminScreenImg.getAttribute("src") && adminScreenImg.style.display !== "none") {
          return adminScreenImg;
        }
        return adminScreenView;
      };

      const adminScreenFittedPoint = (event) => {
        const media = adminScreenActiveMedia();
        if (!media) {
          return null;
        }
        const rect = media.getBoundingClientRect();
        if (!rect.width || !rect.height) {
          return null;
        }
        let mediaWidth = Number(media.videoWidth || media.naturalWidth || rect.width);
        let mediaHeight = Number(media.videoHeight || media.naturalHeight || rect.height);
        if (!mediaWidth || !mediaHeight) {
          mediaWidth = rect.width;
          mediaHeight = rect.height;
        }
        const scale = Math.min(rect.width / mediaWidth, rect.height / mediaHeight);
        const fittedWidth = mediaWidth * scale;
        const fittedHeight = mediaHeight * scale;
        const left = rect.left + ((rect.width - fittedWidth) / 2);
        const top = rect.top + ((rect.height - fittedHeight) / 2);
        return {
          x: Math.max(0, Math.min(1, (event.clientX - left) / fittedWidth)),
          y: Math.max(0, Math.min(1, (event.clientY - top) / fittedHeight)),
        };
      };

      const sendAdminScreenControlDataChannel = (commands = []) => {
        if (!adminScreenControlChannelOpen() || !Array.isArray(commands) || !commands.length) {
          return false;
        }
        try {
          adminScreenControlChannel.send(JSON.stringify({ type: "screen-control", commands }));
          return true;
        } catch (error) {
          return false;
        }
      };

      const flushAdminScreenControlQueue = async () => {
        if (adminScreenControlSending || !adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active" || !adminScreenControlQueue.length) {
          return;
        }
        adminScreenControlSending = true;
        adminScreenControlLastSentAt = Date.now();
        const commands = adminScreenControlQueue.splice(0, 32);
        if (sendAdminScreenControlDataChannel(commands)) {
          adminScreenControlSending = false;
          if (adminScreenControlQueue.length) {
            adminScreenControlTimer = window.setTimeout(() => void flushAdminScreenControlQueue(), 16);
          }
          return;
        }
        const httpCommands = commands;
        if (!httpCommands.length) {
          adminScreenControlSending = false;
          if (adminScreenControlQueue.length) {
            adminScreenControlTimer = window.setTimeout(() => void flushAdminScreenControlQueue(), 120);
          }
          return;
        }
        try {
          const { payload } = await fetchAuthJson("/screen/auth-admin/control", {
            method: "POST",
            body: JSON.stringify({
              username: adminScreenUser,
              session: adminScreenSession.id,
              commands: httpCommands,
            }),
          });
          if (payload && payload.session) {
            adminScreenSession = payload.session;
          }
        } catch (error) {
          const important = httpCommands.filter((command) => command && command.dispatch !== false);
          adminScreenControlQueue = important.concat(adminScreenControlQueue).slice(-80);
          if (important.length) {
            setAdminScreenStatus(error && error.message ? error.message : "Could not send screen control.", "error");
          }
        } finally {
          adminScreenControlSending = false;
          if (adminScreenControlQueue.length) {
            adminScreenControlTimer = window.setTimeout(() => void flushAdminScreenControlQueue(), 80);
          }
        }
      };

      const queueAdminScreenControl = (command = {}, urgent = false) => {
        if (!adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active") {
          return;
        }
        if (command.type === "cursor" && command.dispatch === false) {
          for (let index = adminScreenControlQueue.length - 1; index >= 0; index -= 1) {
            const item = adminScreenControlQueue[index];
            if (item && item.type === "cursor" && item.dispatch === false) {
              adminScreenControlQueue.splice(index, 1);
              break;
            }
          }
        }
        adminScreenControlQueue.push(command);
        adminScreenControlQueue = adminScreenControlQueue.slice(-80);
        const elapsed = Date.now() - Number(adminScreenControlLastSentAt || 0);
        const delay = urgent ? 0 : (adminScreenControlChannelOpen() ? Math.max(8, 24 - elapsed, 0) : Math.max(35, 90 - elapsed, 0));
        if (adminScreenControlTimer) {
          window.clearTimeout(adminScreenControlTimer);
        }
        adminScreenControlTimer = window.setTimeout(() => void flushAdminScreenControlQueue(), delay);
      };

      const queueAdminScreenPointer = (event, type, options = {}) => {
        const point = adminScreenFittedPoint(event);
        if (!point) {
          return false;
        }
        queueAdminScreenControl({
          type,
          x: point.x,
          y: point.y,
          visible: options.visible !== false,
          button: Number(event.button || 0),
          buttons: Number(event.buttons || 0),
          ctrl: Boolean(event.ctrlKey),
          alt: Boolean(event.altKey),
          shift: Boolean(event.shiftKey),
          meta: Boolean(event.metaKey),
          dispatch: options.dispatch !== false,
        }, Boolean(options.urgent));
        return true;
      };

      const sendAdminScreenSignal = async (type, data) => {
        if (!adminScreenUser || !adminScreenSession || !type || !data) {
          return;
        }
        await fetchAuthJson("/screen/auth-admin/signal", {
          method: "POST",
          body: JSON.stringify({
            username: adminScreenUser,
            session: adminScreenSession.id,
            type,
            data,
          }),
        });
      };

      const updateAdminScreenMicButton = () => {
        if (!adminScreenMicButton) {
          return;
        }
        adminScreenMicButton.classList.toggle("is-primary", Boolean(adminScreenMicEnabled));
        adminScreenMicButton.classList.toggle("is-active", Boolean(adminScreenMicEnabled));
        adminScreenMicButton.textContent = adminScreenMicEnabled ? "Mic On" : "Mic Off";
        adminScreenMicButton.title = adminScreenMicEnabled
          ? "Admin mic is being sent to the user during this screen session."
          : "Turn on admin mic for the user to hear.";
      };

      const stopAdminScreenMicRelay = () => {
        adminScreenMicRelayAutoRestart = false;
        if (adminScreenMicSegmentTimer) {
          window.clearTimeout(adminScreenMicSegmentTimer);
          adminScreenMicSegmentTimer = 0;
        }
        adminScreenMicSending = false;
        if (adminScreenMicRecorder && adminScreenMicRecorder.state !== "inactive") {
          try { adminScreenMicRecorder.stop(); } catch (error) {}
        }
        adminScreenMicRecorder = null;
      };

      const postAdminScreenMicChunk = async (blob) => {
        if (!adminScreenMicEnabled || !adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active" || !blob || !blob.size) {
          return;
        }
        const data = await fileToDataUrl(blob);
        await fetchAuthJson("/screen/auth-admin/audio-chunk", {
          method: "POST",
          body: JSON.stringify({
            username: adminScreenUser,
            session: adminScreenSession.id,
            data,
            mime: blob.type || "audio/webm",
          }),
          timeoutMs: 5000,
        });
      };

      const startAdminScreenMicRelay = () => {
        if (!adminScreenMicEnabled || !adminScreenMicStream || !adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active" || !window.MediaRecorder) {
          return;
        }
        if (adminScreenMicRecorder && adminScreenMicRecorder.state !== "inactive") {
          return;
        }
        const tracks = screenAudioTracks(adminScreenMicStream);
        if (!tracks.length) {
          return;
        }
        let recorder = null;
        try {
          const audioStream = new MediaStream(tracks);
          const mimeType = learnerChatRecorderMimeType();
          recorder = new MediaRecorder(audioStream, mimeType ? { mimeType } : undefined);
        } catch (error) {
          setAdminScreenStatus("Could not start admin mic relay.", "error");
          return;
        }
        adminScreenMicRecorder = recorder;
        adminScreenMicSending = true;
        adminScreenMicRelayAutoRestart = true;
        recorder.addEventListener("dataavailable", (event) => {
          if (event.data && event.data.size) {
            void postAdminScreenMicChunk(event.data).catch(() => {});
          }
        });
        recorder.addEventListener("stop", () => {
          if (adminScreenMicRecorder === recorder) {
            adminScreenMicRecorder = null;
          }
          adminScreenMicSending = false;
          if (adminScreenMicRelayAutoRestart && adminScreenMicEnabled && adminScreenMicStream && adminScreenSession && adminScreenSession.state === "active") {
            window.setTimeout(() => startAdminScreenMicRelay(), 45);
          }
        });
        try {
          recorder.start();
          adminScreenMicSegmentTimer = window.setTimeout(() => {
            adminScreenMicSegmentTimer = 0;
            if (adminScreenMicRecorder === recorder && recorder.state !== "inactive") {
              try { recorder.stop(); } catch (error) {}
            }
          }, Math.max(520, LEARNER_SCREEN_AUDIO_RELAY_MS * 3));
          setAdminScreenStatus("Admin mic relay is sending to user.", "ok");
        } catch (error) {
          adminScreenMicRecorder = null;
          adminScreenMicSending = false;
          setAdminScreenStatus("Could not start admin mic relay.", "error");
        }
      };

      const stopAdminScreenMic = () => {
        stopAdminScreenMicRelay();
        if (adminScreenMicStream) {
          adminScreenMicStream.getTracks().forEach((track) => {
            try { track.stop(); } catch (error) {}
          });
        }
        adminScreenMicStream = null;
        adminScreenMicEnabled = false;
        updateAdminScreenMicButton();
      };

      const startAdminScreenMic = async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          setAdminScreenStatus("Browser does not support admin mic capture.", "error");
          return;
        }
        if (!adminScreenMicStream) {
          adminScreenMicStream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
          });
          adminScreenMicStream.getAudioTracks().forEach((track) => {
            track.addEventListener("ended", () => {
              stopAdminScreenMic();
              setAdminScreenStatus("Admin mic was turned off by the browser.", "error");
            });
          });
        }
        adminScreenMicEnabled = true;
        updateAdminScreenMicButton();
        startAdminScreenMicRelay();
        if (adminScreenSession && adminScreenSession.state === "active" && adminScreenTransportPreference !== "relay") {
          await reconnectAdminScreen();
        }
      };

      const toggleAdminScreenMic = async () => {
        if (adminScreenMicEnabled) {
          stopAdminScreenMic();
          setAdminScreenStatus("Admin mic off.", "ok");
          return;
        }
        try {
          await startAdminScreenMic();
        } catch (error) {
          stopAdminScreenMic();
          setAdminScreenStatus(error && error.message ? error.message : "Could not turn on admin mic.", "error");
        }
      };

      const startAdminScreenPeer = async () => {
        if (!adminScreenSession || adminScreenSession.state !== "active" || adminScreenPeer || !window.RTCPeerConnection) {
          return;
        }
        if (typeof refreshServerSettings === "function") {
          await refreshServerSettings();
        }
        if (adminScreenTransportPreference === "relay") {
          delete webRtcConfig.iceTransportPolicy;
          setAdminScreenStatus(`Server relay mode for ${adminScreenUser}. WebRTC is paused.`, "ok");
          setAdminScreenPlaceholder("Relay mode. Waiting for server relay frame...");
          setAdminScreenTransportMode("relay-only", "mode-relay-active");
          return;
        }
        if (adminScreenTransportPreference === "realtime") {
          delete webRtcConfig.iceTransportPolicy;
        }
        setAdminScreenStatus(webRtcHasTurnRelay()
          ? `Direct WebRTC connecting to ${adminScreenUser} with relay support...`
          : `Direct WebRTC connecting to ${adminScreenUser}; server relay fallback is ready...`);
        setAdminScreenPlaceholder("Connected. Waiting for direct video or server relay...");
        adminScreenPeer = new RTCPeerConnection(webRtcConfig);
        adminScreenControlChannel = adminScreenPeer.createDataChannel("screen-control", { ordered: true });
        adminScreenControlChannel.addEventListener("open", () => {
          setAdminScreenStatus("Direct control channel connected.", "ok");
          setAdminScreenTransportMode("webrtc-datachannel", "datachannel-open");
          void flushAdminScreenControlQueue();
        });
        const updateAdminScreenPeerStatus = () => {
          if (!adminScreenPeer) {
            return;
          }
          const state = adminScreenPeer.connectionState || adminScreenPeer.iceConnectionState || "";
          if (state === "connected" || adminScreenPeer.iceConnectionState === "completed") {
            setAdminScreenStatus(`Direct WebRTC connected to ${adminScreenUser}.`, "ok");
            if (adminScreenWebRtcVideoLive()) {
              setAdminScreenPlaceholder("", true);
            } else {
              setAdminScreenPlaceholder("Direct WebRTC connected. Waiting for video frame...");
            }
          } else if (state === "failed" || state === "disconnected") {
            setAdminScreenStatus(`Direct WebRTC ${state}. Server relay fallback is still polling.`, "error");
            setAdminScreenPlaceholder("Direct video lost. Waiting for server relay frame...");
            setAdminScreenTransportMode(`webrtc-${state}`, `webrtc-${state}`);
          } else if (state) {
            setAdminScreenStatus(`Direct WebRTC ${state}...`);
          }
        };
        adminScreenPeer.addEventListener("connectionstatechange", updateAdminScreenPeerStatus);
        adminScreenPeer.addEventListener("iceconnectionstatechange", updateAdminScreenPeerStatus);
        adminScreenPeer.addEventListener("icecandidate", (event) => {
          if (event.candidate) {
            void sendAdminScreenSignal("candidate", event.candidate.toJSON()).catch(() => {});
          }
        });
        adminScreenPeer.addEventListener("track", (event) => {
          if (event.track && event.track.kind === "audio") {
            const audio = ensureAdminScreenRemoteAudio();
            audio.srcObject = event.streams && event.streams[0] ? event.streams[0] : new MediaStream([event.track]);
            audio.play().catch(() => {
              setAdminScreenStatus("Direct screen audio is ready. Click inside the screen panel if the browser blocks autoplay.");
            });
            return;
          }
          if (adminScreenVideo) {
            adminScreenVideo.srcObject = event.streams && event.streams[0] ? event.streams[0] : new MediaStream([event.track]);
            adminScreenVideo.style.display = "block";
            setAdminScreenTransportMode("webrtc-video", "webrtc-track");
          }
          if (adminScreenImg) {
            adminScreenImg.style.display = "none";
          }
          if (adminScreenPlaceholder) {
            setAdminScreenPlaceholder("", true);
          }
        });
        if (adminScreenMicEnabled && adminScreenMicStream) {
          screenAudioTracks(adminScreenMicStream).forEach((track) => {
            try {
              adminScreenPeer.addTrack(track, adminScreenMicStream);
            } catch (error) {
            }
          });
        }
        try {
          adminScreenPeer.addTransceiver("video", { direction: "recvonly" });
        } catch (error) {
        }
        try {
          adminScreenPeer.addTransceiver("audio", { direction: "recvonly" });
        } catch (error) {
        }
        const offer = await adminScreenPeer.createOffer({ offerToReceiveVideo: true, offerToReceiveAudio: true });
        await adminScreenPeer.setLocalDescription(offer);
        await sendAdminScreenSignal("offer", adminScreenPeer.localDescription.toJSON());
        adminScreenOfferSent = true;
      };

      const pollAdminScreenSignals = async () => {
        if (!adminScreenOpen || !adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active") {
          return;
        }
        try {
          const { payload } = await fetchAuthJson(`/screen/auth-admin/signal?username=${encodeURIComponent(adminScreenUser)}&session=${encodeURIComponent(adminScreenSession.id)}&after=${encodeURIComponent(String(adminScreenRemoteCandidateId || 0))}`);
          if (payload.session && payload.session.id) {
            adminScreenSession = payload.session;
          }
          if (!adminScreenPeer) {
            await startAdminScreenPeer();
          }
          if (payload.answer && adminScreenPeer && !adminScreenAnswerSet) {
            await adminScreenPeer.setRemoteDescription(new RTCSessionDescription(payload.answer));
            adminScreenAnswerSet = true;
          }
          const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
          for (const item of candidates) {
            adminScreenRemoteCandidateId = Math.max(adminScreenRemoteCandidateId, Number(item.id || 0));
            if (item.candidate && adminScreenPeer && adminScreenAnswerSet) {
              try {
                await adminScreenPeer.addIceCandidate(new RTCIceCandidate(item.candidate));
              } catch (error) {
              }
            }
          }
        } catch (error) {
          setAdminScreenStatus(error && error.message ? error.message : "Could not poll screen signal.", "error");
        } finally {
          if (adminScreenOpen && adminScreenSession && adminScreenSession.state === "active") {
            adminScreenPollTimer = window.setTimeout(() => void pollAdminScreenSignals(), 900);
          }
        }
      };

      const pollAdminScreenFrame = async () => {
        if (adminScreenFrameTimer) {
          window.clearTimeout(adminScreenFrameTimer);
          adminScreenFrameTimer = 0;
        }
        if (!adminScreenOpen || !adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active") {
          return;
        }
        const webRtcLive = adminScreenWebRtcVideoLive();
        try {
          const { payload } = await fetchAuthJson(`/screen/auth-admin/frame?username=${encodeURIComponent(adminScreenUser)}&session=${encodeURIComponent(adminScreenSession.id)}&after=${encodeURIComponent(String(adminScreenFrameId || 0))}`);
          if (payload.session && payload.session.id) {
            adminScreenSession = payload.session;
          }
          const frame = payload.frame || null;
          if (frame && frame.data) {
            const incomingFrameId = Number(frame.id || 0);
            const frameSeenAt = Date.now();
            if (incomingFrameId > adminScreenRelayLastFrameId && adminScreenRelayLastFrameAt) {
              const elapsedSeconds = Math.max(0.001, (frameSeenAt - adminScreenRelayLastFrameAt) / 1000);
              adminScreenRelayFps = (incomingFrameId - adminScreenRelayLastFrameId) / elapsedSeconds;
            } else if (incomingFrameId <= adminScreenRelayLastFrameId) {
              adminScreenRelayFps = 0;
            }
            adminScreenRelayLastFrameAt = frameSeenAt;
            adminScreenRelayLastFrameId = incomingFrameId;
            adminScreenRelayFrameChars = String(frame.data || "").length;
            adminScreenRelayFrameWidth = Number(frame.width || 0);
            adminScreenRelayFrameHeight = Number(frame.height || 0);
            adminScreenFrameId = Math.max(adminScreenFrameId, incomingFrameId);
            if (adminScreenImg) {
              adminScreenImg.src = String(frame.data || "");
              adminScreenImg.style.display = webRtcLive ? "none" : "block";
            }
            if (!webRtcLive) {
              if (adminScreenVideo) {
                adminScreenVideo.style.display = "none";
              }
              setAdminScreenPlaceholder("", true);
              setAdminScreenStatus(`Server relay screen active for ${adminScreenUser}.`, "ok");
              setAdminScreenTransportMode("server-relay-frame", "server-relay-frame");
            }
          } else if (!webRtcLive) {
            setAdminScreenPlaceholder("Waiting for server relay frame...");
          }
        } catch (error) {
          if (!webRtcLive) {
            setAdminScreenStatus(error && error.message ? error.message : "Could not poll screen relay frame.", "error");
          }
        } finally {
          if (adminScreenOpen && adminScreenUser && adminScreenSession && adminScreenSession.state === "active") {
            if (!adminScreenAudioPollTimer) {
              scheduleAdminScreenAudioPolling(0);
            }
            const delay = adminScreenWebRtcVideoLive() ? 1500 : LEARNER_SCREEN_PREVIEW_INTERVAL_MS;
            adminScreenFrameTimer = window.setTimeout(() => void pollAdminScreenFrame(), delay);
          }
        }
      };

      const adminScreenUserHasLiveSession = (user = {}) => {
        const screen = user && user.screen && typeof user.screen === "object" ? user.screen : {};
        const stream = user && user.stream && typeof user.stream === "object" ? user.stream : {};
        const screenState = clean(screen.state).toLowerCase();
        const streamState = clean(stream.state).toLowerCase();
        return Boolean(
          (screen.id && ["pending_user", "active"].includes(screenState)) ||
          (stream.id && ["pending_admin", "pending_user", "active"].includes(streamState)) ||
          Number(screen.frame_id || screen.frameId || 0) > 0
        );
      };

      const adminScreenVisibleUsers = () => adminScreenUsers.filter((user) => {
        const username = clean(user && user.username);
        if (!username) {
          return false;
        }
        if (username.toLowerCase() === clean(currentAuthUsername).toLowerCase() && !adminScreenUserHasLiveSession(user)) {
          return false;
        }
        return Boolean(user.online || adminScreenUserHasLiveSession(user));
      });

      const renderAdminScreenUsers = () => {
        if (!adminScreenList) {
          return;
        }
        adminScreenList.textContent = "";
        const users = adminScreenVisibleUsers();
        if (!users.length) {
          const empty = document.createElement("div");
          empty.className = "ft-admin-screen-user";
          empty.textContent = "No online or active screen users.";
          adminScreenList.appendChild(empty);
          return;
        }
        users.forEach((user) => {
          const username = clean(user.username);
          const screenState = clean(user.screen && user.screen.state);
          const streamState = clean(user.stream && user.stream.state);
          const liveLabel = user.online ? "online" : "session active";
          const row = document.createElement("article");
          row.className = "ft-admin-screen-user" + (username === adminScreenUser ? " is-active" : "");
          const title = document.createElement("div");
          title.className = "ft-admin-screen-user-title";
          title.textContent = username;
          const meta = document.createElement("div");
          meta.className = "ft-admin-screen-user-meta";
          meta.textContent = `State: ${liveLabel} | Last seen: ${clean(user.last_seen || "")}${screenState ? ` | Screen: ${screenState}` : ""}${streamState ? ` | Stream: ${streamState}` : ""}`;
          const actions = document.createElement("div");
          actions.className = "ft-admin-screen-user-actions";
          const connect = document.createElement("button");
          connect.className = "ft-admin-screen-user-action is-primary";
          connect.type = "button";
          connect.textContent = screenState === "active" ? "Open" : "Screen";
          connect.addEventListener("click", () => void connectAdminScreenUser(username, user.screen || null));
          actions.appendChild(connect);
          row.append(title, meta, actions);
          adminScreenList.appendChild(row);
        });
      };

      const loadAdminScreenUsers = async () => {
        if (!currentAuthIsAdmin) {
          setAdminScreenStatus("Only admins can open user screens.", "error");
          return;
        }
        try {
          const { payload } = await fetchAuthJson("/screen/auth-admin/state");
          adminScreenUsers = Array.isArray(payload.users) ? payload.users : [];
          renderAdminScreenUsers();
          setAdminScreenStatus(`Shown: ${adminScreenVisibleUsers().length} | Online: ${Number(payload.online_count || 0)} | Total: ${adminScreenUsers.length}`, "ok");
        } catch (error) {
          setAdminScreenStatus(error && error.message ? error.message : "Could not load online users.", "error");
        }
      };

      const connectAdminScreenUser = async (username, existingSession = null) => {
        adminScreenUser = clean(username);
        resetAdminScreenTransport();
        setAdminScreenPlaceholder("Waiting for user screen permission...");
        try {
          let session = existingSession && existingSession.id ? existingSession : null;
          if (!session || !["pending_user", "active"].includes(session.state || "")) {
            const { payload } = await fetchAuthJson("/screen/auth-admin/request", {
              method: "POST",
              body: JSON.stringify({ username: adminScreenUser }),
            });
            session = payload.session || null;
            adminScreenUsers = Array.isArray(payload.users) ? payload.users : adminScreenUsers;
          }
          adminScreenSession = session;
          renderAdminScreenUsers();
          setAdminScreenStatus(session && session.state === "active" ? `Connected to ${adminScreenUser}.` : `Requested ${adminScreenUser}. Waiting...`);
          if (adminScreenSession && adminScreenSession.state === "active") {
            setAdminScreenPlaceholder("Connected. Waiting for direct video or server relay...");
            startAdminScreenMicRelay();
            if (adminScreenTransportPreference !== "relay") {
              await startAdminScreenPeer();
              void pollAdminScreenSignals();
            } else {
              await startAdminScreenPeer();
            }
            void pollAdminScreenFrame();
          } else {
            adminScreenPollTimer = window.setTimeout(() => void refreshAdminScreenActiveSession(), 1000);
          }
        } catch (error) {
          setAdminScreenStatus(error && error.message ? error.message : "Could not connect screen.", "error");
        }
      };

      const refreshAdminScreenActiveSession = async () => {
        if (!adminScreenOpen || !adminScreenUser) {
          return;
        }
        await loadAdminScreenUsers();
        const record = adminScreenUsers.find((user) => clean(user.username) === adminScreenUser);
        if (record && record.screen && record.screen.id) {
          adminScreenSession = record.screen;
          if (record.screen.state === "active") {
            setAdminScreenStatus(`Connected to ${adminScreenUser}. Starting direct WebRTC...`, "ok");
            setAdminScreenPlaceholder("Connected. Waiting for direct video or server relay...");
            startAdminScreenMicRelay();
            if (adminScreenTransportPreference !== "relay") {
              await startAdminScreenPeer();
              void pollAdminScreenSignals();
            } else {
              await startAdminScreenPeer();
            }
            void pollAdminScreenFrame();
            return;
          }
        }
        if (adminScreenOpen && adminScreenUser) {
          adminScreenPollTimer = window.setTimeout(() => void refreshAdminScreenActiveSession(), 1200);
        }
      };

      const openAdminScreenModal = async () => {
        if (!currentAuthIsAdmin) {
          showTopNotice("Only admins can control user screens.", "error", { duration: 3000 });
          return;
        }
        loadAdminScreenTransportPreference();
        adminScreenOpen = true;
        updateAdminScreenMicButton();
        setMobileToolsOpen(false);
        if (adminScreenModal) {
          adminScreenModal.classList.add("is-open");
          adminScreenModal.setAttribute("aria-hidden", "false");
        }
        await loadAdminScreenUsers();
      };

      const closeAdminScreenModal = () => {
        adminScreenOpen = false;
        resetAdminScreenTransport();
        stopAdminScreenMic();
        adminScreenUser = "";
        adminScreenSession = null;
        if (adminScreenModal) {
          adminScreenModal.classList.remove("is-open");
          adminScreenModal.setAttribute("aria-hidden", "true");
        }
      };

      const stopAdminScreenSession = async () => {
        if (!adminScreenUser || !adminScreenSession) {
          return;
        }
        try {
          await fetchAuthJson("/screen/auth-admin/action", {
            method: "POST",
            body: JSON.stringify({ username: adminScreenUser, session: adminScreenSession.id, action: "end" }),
          });
        } catch (error) {
        }
        resetAdminScreenTransport();
        stopAdminScreenMic();
        adminScreenSession = null;
        await loadAdminScreenUsers();
      };

      const reconnectAdminScreen = async () => {
        if (!adminScreenUser) {
          return;
        }
        const username = adminScreenUser;
        const session = adminScreenSession;
        resetAdminScreenTransport();
        adminScreenSession = session;
        if (adminScreenSession && adminScreenSession.state === "active") {
          startAdminScreenMicRelay();
          if (adminScreenTransportPreference !== "relay") {
            await startAdminScreenPeer();
            void pollAdminScreenSignals();
          } else {
            await startAdminScreenPeer();
          }
          void pollAdminScreenFrame();
        } else {
          await connectAdminScreenUser(username, session);
        }
      };

      const normalizeQuestionMotionMode = (value) => clean(value).toLowerCase() === "hover" ? "hover" : "always";

      const questionMotionStorageKey = () => {
        const username = clean(currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase();
        return `${QUESTION_MOTION_KEY}:${username || "guest"}`;
      };

      const questionSideCardsStorageKey = () => {
        const username = clean(currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase();
        return `${QUESTION_SIDE_CARDS_KEY}:${username || "guest"}`;
      };

      const questionAnimationStorageKey = () => {
        const username = clean(currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase();
        return `${QUESTION_ANIMATION_KEY}:${username || "guest"}`;
      };

      const loadQuestionMotionSettings = () => {
        let saved = {};
        try {
          saved = JSON.parse(localStorage.getItem(questionMotionStorageKey()) || "{}") || {};
        } catch (error) {
          saved = {};
        }
        questionMotionSettings = {
          picture: normalizeQuestionMotionMode(saved.picture),
          audio: normalizeQuestionMotionMode(saved.audio),
        };
        return questionMotionSettings;
      };

      const saveQuestionMotionSettings = () => {
        try {
          localStorage.setItem(questionMotionStorageKey(), JSON.stringify(questionMotionSettings));
        } catch (error) {
        }
      };

      const loadQuestionSideCardsSettings = () => {
        try {
          const saved = JSON.parse(localStorage.getItem(questionSideCardsStorageKey()) || "{}") || {};
          questionCardEffectsPaused = Boolean(saved.effects_paused ?? saved.effectsPaused ?? saved.hidden);
        } catch (error) {
          questionCardEffectsPaused = false;
        }
        return questionCardEffectsPaused;
      };

      const loadQuestionAnimationSettings = () => {
        try {
          const saved = JSON.parse(localStorage.getItem(questionAnimationStorageKey()) || "{}") || {};
          questionAnimationsPaused = Boolean(saved.paused ?? saved.animation_paused ?? saved.animationPaused ?? saved.off);
        } catch (error) {
          questionAnimationsPaused = false;
        }
        return questionAnimationsPaused;
      };

      const saveQuestionSideCardsSettings = () => {
        try {
          localStorage.setItem(questionSideCardsStorageKey(), JSON.stringify({
            effects_paused: Boolean(questionCardEffectsPaused),
            hidden: Boolean(questionCardEffectsPaused),
          }));
        } catch (error) {
        }
      };

      const saveQuestionAnimationSettings = (pausedValue = questionAnimationsPaused) => {
        try {
          localStorage.setItem(questionAnimationStorageKey(), JSON.stringify({
            paused: Boolean(pausedValue),
            enabled: !Boolean(pausedValue),
          }));
        } catch (error) {
        }
      };

      const applyQuestionMotionPayload = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        const motion = source.question_motion || source.questionMotion || source.motion;
        if (!motion || typeof motion !== "object") {
          return false;
        }
        questionMotionSettings = {
          picture: normalizeQuestionMotionMode(motion.picture),
          audio: normalizeQuestionMotionMode(motion.audio),
        };
        saveQuestionMotionSettings();
        return true;
      };

      const applyQuestionSideCardsPayload = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        let cards = null;
        if (Object.prototype.hasOwnProperty.call(source, "question_side_cards")) {
          cards = source.question_side_cards;
        } else if (Object.prototype.hasOwnProperty.call(source, "questionSideCards")) {
          cards = source.questionSideCards;
        }
        if (!cards || typeof cards !== "object") {
          return false;
        }
        questionCardEffectsPaused = Boolean(cards.effects_paused ?? cards.effectsPaused ?? cards.hidden);
        saveQuestionSideCardsSettings();
        applyQuestionSideCardsPreference();
        return true;
      };

      const applyQuestionAnimationPayload = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        let animation = null;
        if (Object.prototype.hasOwnProperty.call(source, "question_animation")) {
          animation = source.question_animation;
        } else if (Object.prototype.hasOwnProperty.call(source, "questionAnimation")) {
          animation = source.questionAnimation;
        }
        if (!animation || typeof animation !== "object") {
          return false;
        }
        const rawPaused = animation.paused ?? animation.animation_paused ?? animation.animationPaused ?? animation.off;
        questionAnimationsPaused = rawPaused !== undefined
          ? Boolean(rawPaused)
          : (animation.enabled !== undefined ? !Boolean(animation.enabled) : false);
        saveQuestionAnimationSettings();
        applyQuestionAnimationPreference();
        return true;
      };

      const syncQuestionMotionSettingsToServer = async () => {
        if (!authToken) {
          return;
        }
        try {
          await fetchAuthJson("/auth/preferences", {
            method: "POST",
            body: JSON.stringify({
              question_motion: questionMotionSettings,
              question_animation: {
                paused: Boolean(questionAnimationsPaused),
                enabled: !questionAnimationsPaused,
              },
              question_side_cards: {
                effects_paused: Boolean(questionCardEffectsPaused),
                hidden: Boolean(questionCardEffectsPaused),
              },
            }),
          });
        } catch (error) {
          // Local storage remains the offline fallback.
        }
      };

      const applyQuestionMotionSettings = () => {
        if (qPictureCard) {
          qPictureCard.dataset.motion = "always";
        }
        if (qAudioCard) {
          qAudioCard.dataset.motion = "always";
        }
        if (qPictureMotionButton) {
          qPictureMotionButton.dataset.motion = "decor";
          qPictureMotionButton.textContent = "Portal motion";
          qPictureMotionButton.title = "Decorative portal status.";
        }
        if (qAudioMotionButton) {
          qAudioMotionButton.dataset.motion = "decor";
          qAudioMotionButton.textContent = "Aural orbit";
          qAudioMotionButton.title = "Decorative audio orbit status.";
        }
      };

      const clearQuestionAnimationChargeState = () => {
        if (qAnimationToggle) {
          qAnimationToggle.classList.remove("is-charged");
        }
        if (qAnimationEnergy) {
          qAnimationEnergy.classList.remove("is-charged");
        }
        if (qAnimationPanel) {
          qAnimationPanel.classList.remove("is-energy-charged");
        }
      };

      const setQuestionAnimationChargeState = () => {
        if (qAnimationToggle) {
          qAnimationToggle.classList.remove("is-charged");
          void qAnimationToggle.offsetWidth;
          qAnimationToggle.classList.add("is-charged");
        }
        if (qAnimationEnergy) {
          qAnimationEnergy.classList.remove("is-charged");
          void qAnimationEnergy.offsetWidth;
          qAnimationEnergy.classList.add("is-charged");
        }
        if (qAnimationPanel) {
          qAnimationPanel.classList.remove("is-energy-charged");
          void qAnimationPanel.offsetWidth;
          qAnimationPanel.classList.add("is-energy-charged");
        }
      };

      const setQuestionAnimationControlVisualOn = (options = {}) => {
        const arming = Boolean(options.arming);
        clearQuestionAnimationDischargeState();
        if (qAnimationToggle) {
          qAnimationToggle.classList.remove("is-off");
          qAnimationToggle.classList.add("is-on");
          qAnimationToggle.classList.toggle("is-arming", arming);
          const animationLabel = qAnimationToggle.querySelector(".ft-q-animation-label");
          if (animationLabel) {
            animationLabel.textContent = "Anim on";
          } else {
            qAnimationToggle.textContent = "Anim on";
          }
          qAnimationToggle.setAttribute("aria-pressed", "false");
          qAnimationToggle.title = questionRevealAnimationOverrideActive
            ? "Animation is forced on until the reveal sequence is complete."
            : "Decorative animation is allowed.";
        }
        if (qAnimationEnergy) {
          qAnimationEnergy.classList.remove("is-off");
          qAnimationEnergy.classList.add("is-on");
          qAnimationEnergy.classList.toggle("is-arming", arming);
        }
        if (stageNode) {
          stageNode.classList.remove("is-question-animation-paused");
          stageNode.classList.remove("is-question-idle-static");
        }
      };

      const beginQuestionRevealAnimationOverride = () => {
        if (questionRevealAnimationOverrideActive) {
          setQuestionAnimationControlVisualOn();
          return;
        }
        questionRevealAnimationOverrideActive = true;
        questionRevealAnimationRestorePaused = Boolean(questionAnimationsPaused);
        questionAnimationsPaused = false;
        questionAnimationRebootToken += 1;
        if (questionAnimationChargeTimer) {
          window.clearTimeout(questionAnimationChargeTimer);
          questionAnimationChargeTimer = 0;
        }
        if (questionAnimationRebootTimer) {
          window.clearTimeout(questionAnimationRebootTimer);
          questionAnimationRebootTimer = 0;
        }
        setQuestionAnimationControlVisualOn({ arming: true });
        updateQuestionIdleStaticState();
      };

      const endQuestionRevealAnimationOverride = (options = {}) => {
        if (!questionRevealAnimationOverrideActive) {
          return;
        }
        const shouldPause = Boolean(questionRevealAnimationRestorePaused);
        questionRevealAnimationOverrideActive = false;
        questionAnimationsPaused = shouldPause;
        if (shouldPause) {
          applyQuestionAnimationPreference({ discharge: Boolean(options.discharge) });
        } else {
          restoreQuestionAnimationControlVisuals();
        }
      };

      const applyQuestionAnimationPreference = (options = {}) => {
        if (questionRevealAnimationOverrideActive && !(options && options.forceStored)) {
          if (questionAnimationsPaused) {
            questionRevealAnimationRestorePaused = true;
          }
          questionAnimationsPaused = false;
          setQuestionAnimationControlVisualOn();
          updateQuestionIdleStaticState();
          return;
        }
        const paused = Boolean(questionAnimationsPaused);
        const animateDischarge = Boolean(options && options.discharge && paused && qAnimationEnergy);
        if (questionAnimationDischargeTimer) {
          window.clearTimeout(questionAnimationDischargeTimer);
          questionAnimationDischargeTimer = 0;
        }
        if (qAnimationToggle) {
          qAnimationToggle.classList.remove("is-arming");
          qAnimationToggle.classList.toggle("is-off", paused);
          qAnimationToggle.classList.toggle("is-on", !paused);
          const animationLabel = qAnimationToggle.querySelector(".ft-q-animation-label");
          if (animationLabel) {
            animationLabel.textContent = paused ? "Anim off" : "Anim on";
          } else {
            qAnimationToggle.textContent = paused ? "Anim off" : "Anim on";
          }
          qAnimationToggle.setAttribute("aria-pressed", paused ? "true" : "false");
          qAnimationToggle.title = paused
            ? "Decorative animation is paused after reveal."
            : "Decorative animation is allowed.";
        }
        if (qAnimationEnergy) {
          qAnimationEnergy.classList.remove("is-discharging");
          if (animateDischarge) {
            qAnimationEnergy.classList.remove("is-off");
            qAnimationEnergy.classList.add("is-on");
            void qAnimationEnergy.offsetWidth;
            qAnimationEnergy.classList.add("is-discharging");
            questionAnimationDischargeTimer = window.setTimeout(() => {
              questionAnimationDischargeTimer = 0;
              qAnimationEnergy.classList.remove("is-discharging", "is-on");
              qAnimationEnergy.classList.add("is-off");
            }, questionAnimationEnergyDischargeDuration());
          } else {
            qAnimationEnergy.classList.toggle("is-off", paused);
            qAnimationEnergy.classList.toggle("is-on", !paused);
          }
        }
        if (stageNode) {
          stageNode.classList.toggle("is-question-animation-paused", paused);
        }
        if (!paused && questionCardEffectsPaused) {
          questionCardEffectsPaused = false;
          saveQuestionSideCardsSettings();
          if (qSideCardToggle) {
            qSideCardToggle.classList.remove("is-off");
            qSideCardToggle.textContent = "FX on";
            qSideCardToggle.setAttribute("aria-pressed", "false");
            qSideCardToggle.title = "Animate all Space_Q cards";
          }
          if (qRootCard) {
            qRootCard.classList.remove("is-card-effects-paused");
          }
          if (stageNode) {
            stageNode.classList.remove("is-question-effects-paused");
          }
        }
        updateQuestionIdleStaticState();
        if (paused) {
          window.requestAnimationFrame(() => {
            if (!questionAnimationsPaused) {
              return;
            }
            if (typeof stopSpaceNavigatorMotion === "function") {
              stopSpaceNavigatorMotion();
            }
            if (typeof stopSpaceKeyboardNavigation === "function") {
              stopSpaceKeyboardNavigation();
            }
          });
          questionAnimationRebootToken += 1;
          clearQuestionAnimationChargeState();
          if (questionAnimationChargeTimer) {
            window.clearTimeout(questionAnimationChargeTimer);
            questionAnimationChargeTimer = 0;
          }
          if (questionAnimationRebootTimer) {
            window.clearTimeout(questionAnimationRebootTimer);
            questionAnimationRebootTimer = 0;
          }
          if (stageNode) {
            stageNode.classList.remove("is-question-animation-rebooting");
            stageNode.classList.remove("is-question-picture-replay-resetting");
            stageNode.classList.remove("is-question-reboot-staging");
            clearQuestionRebootPhaseClasses();
          }
          if (qAnimationToggle) {
            qAnimationToggle.classList.remove("is-arming");
          }
          if (qAnimationEnergy) {
            qAnimationEnergy.classList.remove("is-arming");
          }
          document.documentElement.classList.remove("ft-debug-animations-paused");
        }
      };

      const pulseQuestionRebootCards = (targetNodes = null) => {
        if (!stageNode || typeof Element === "undefined") {
          return;
        }
        const targets = Array.isArray(targetNodes)
          ? targetNodes.filter(Boolean)
          : Array.from(stageNode.querySelectorAll([
            ".ft-q-root-card:not(.is-hidden)",
            ".ft-q-audio-card.is-live",
            ".ft-q-question-card.is-live",
            ".ft-q-info-card.is-live",
            ".ft-q-root-info-card.is-live",
            ".ft-q-picture-answer-card.is-live",
          ].join(",")));
        targets.forEach((node) => {
          if (!node || node.classList.contains("ft-q-picture-card") || typeof node.animate !== "function") {
            return;
          }
          const rect = node.getBoundingClientRect();
          if (rect.width <= 0 || rect.height <= 0) {
            return;
          }
          try {
            node.getAnimations()
              .filter((animation) => animation && animation.id === "question-reboot-pulse")
              .forEach((animation) => animation.cancel());
          } catch (error) {
          }
          try {
            const animation = node.animate([
              { opacity: 1, filter: "brightness(0.92) saturate(0.9)" },
              { opacity: 1, filter: "brightness(1.48) saturate(1.28)" },
              { opacity: 1, filter: "brightness(1) saturate(1)" },
            ], {
              duration: 760,
              easing: "cubic-bezier(.16, .84, .22, 1)",
              fill: "none",
            });
            animation.id = "question-reboot-pulse";
          } catch (error) {
          }
        });
      };

      const questionRebootPhaseClasses = [
        "is-question-reboot-regions",
        "is-question-reboot-rails",
        "is-question-reboot-prompt",
        "is-question-reboot-answers",
        "is-question-reboot-electrons",
      ];

      const clearQuestionRebootPhaseClasses = () => {
        if (stageNode) {
          questionRebootPhaseClasses.forEach((className) => stageNode.classList.remove(className));
        }
      };

      const queueQuestionRebootPhase = (className, delayMs, token = questionAnimationRebootToken) => {
        window.setTimeout(() => {
          if (
            token !== questionAnimationRebootToken
            || !stageNode
            || questionAnimationsPaused
            || !stageNode.classList.contains("is-question-animation-rebooting")
          ) {
            return;
          }
          stageNode.classList.add(className);
        }, Math.max(0, Number(delayMs) || 0));
      };

      const queueQuestionPicturePromptStartupPhase = (className, delayMs, token) => {
        window.setTimeout(() => {
          if (
            token !== questionRevealToken
            || !stageNode
            || !questionModeActive
            || !stageNode.classList.contains("is-question-picture-prompt-startup")
          ) {
            return;
          }
          stageNode.classList.add(className);
          scheduleQuestionSideLayout();
        }, Math.max(0, Number(delayMs) || 0));
      };

      const startQuestionPicturePromptStartupSequence = (token = questionRevealToken) => {
        if (!stageNode || !questionModeActive) {
          return;
        }
        stageNode.classList.remove("is-question-picture-prompt-startup");
        clearQuestionRebootPhaseClasses();
        void stageNode.offsetWidth;
        stageNode.classList.add("is-question-picture-prompt-startup");
        queueQuestionPicturePromptStartupPhase("is-question-reboot-regions", 80, token);
        queueQuestionPicturePromptStartupPhase("is-question-reboot-rails", 700, token);
        queueQuestionPicturePromptStartupPhase("is-question-reboot-prompt", 1160, token);
        queueQuestionPicturePromptStartupPhase("is-question-reboot-answers", 1500, token);
        queueQuestionPicturePromptStartupPhase("is-question-reboot-electrons", 1660, token);
        window.setTimeout(() => {
          if (token !== questionRevealToken || !stageNode) {
            return;
          }
          stageNode.classList.remove("is-question-picture-prompt-startup");
          clearQuestionRebootPhaseClasses();
          updateQuestionIdleStaticState();
        }, 3300);
      };

      const isQuestionAnimationRebootCurrent = (token) => Boolean(
        token === questionAnimationRebootToken
        && stageNode
        && questionModeActive
        && !questionAnimationsPaused
        && stageNode.classList.contains("is-question-reboot-staging")
      );

      const panQuestionAnimationRebootTo = (targetNode, token, onDone = null, duration = 720) => {
        if (!isQuestionAnimationRebootCurrent(token)) {
          return false;
        }
        if (!targetNode) {
          if (typeof onDone === "function") {
            window.requestAnimationFrame(onDone);
          }
          return false;
        }
        panQuestionCameraTo(targetNode, () => {
          if (isQuestionAnimationRebootCurrent(token) && typeof onDone === "function") {
            onDone();
          }
        }, duration);
        return true;
      };

      const questionAnimationEnergyChargeDuration = () => {
        const segmentCount = qAnimationEnergy
          ? Math.max(1, qAnimationEnergy.querySelectorAll("span").length)
          : 1;
        return QUESTION_ANIMATION_ENERGY_SEGMENT_MS
          + ((segmentCount - 1) * QUESTION_ANIMATION_ENERGY_SEGMENT_DELAY_MS)
          + QUESTION_ANIMATION_ENERGY_SETTLE_MS;
      };

      const questionAnimationEnergyDischargeDuration = () => {
        const segmentCount = qAnimationEnergy
          ? Math.max(1, qAnimationEnergy.querySelectorAll("span").length)
          : 1;
        return QUESTION_ANIMATION_ENERGY_DISCHARGE_MS
          + ((segmentCount - 1) * QUESTION_ANIMATION_ENERGY_DISCHARGE_DELAY_MS)
          + QUESTION_ANIMATION_ENERGY_DISCHARGE_SETTLE_MS;
      };

      const clearQuestionAnimationDischargeState = () => {
        if (questionAnimationDischargeTimer) {
          window.clearTimeout(questionAnimationDischargeTimer);
          questionAnimationDischargeTimer = 0;
        }
        if (qAnimationEnergy) {
          qAnimationEnergy.classList.remove("is-discharging");
        }
      };

      const restoreQuestionAnimationControlVisuals = () => {
        if (questionRevealAnimationOverrideActive) {
          setQuestionAnimationControlVisualOn();
          return;
        }
        const paused = Boolean(questionAnimationsPaused);
        if (qAnimationToggle) {
          qAnimationToggle.classList.toggle("is-off", paused);
          qAnimationToggle.classList.toggle("is-on", !paused);
          const animationLabel = qAnimationToggle.querySelector(".ft-q-animation-label");
          if (animationLabel) {
            animationLabel.textContent = paused ? "Anim off" : "Anim on";
          } else {
            qAnimationToggle.textContent = paused ? "Anim off" : "Anim on";
          }
          qAnimationToggle.setAttribute("aria-pressed", paused ? "true" : "false");
          qAnimationToggle.title = paused
            ? "Decorative animation is paused after reveal."
            : "Decorative animation is allowed.";
        }
        if (qAnimationEnergy) {
          qAnimationEnergy.classList.remove("is-arming");
          qAnimationEnergy.classList.toggle("is-off", paused);
          qAnimationEnergy.classList.toggle("is-on", !paused);
        }
        if (stageNode) {
          stageNode.classList.toggle("is-question-animation-paused", paused);
        }
        updateQuestionIdleStaticState();
      };

      const clearQuestionIntroBootState = () => {
        questionIntroBootToken += 1;
        if (questionIntroBootTimer) {
          window.clearTimeout(questionIntroBootTimer);
          questionIntroBootTimer = 0;
        }
        if (stageNode) {
          stageNode.classList.remove("is-question-intro-booting");
        }
        if (qAnimationToggle) {
          qAnimationToggle.classList.remove("is-arming");
        }
        if (qAnimationEnergy) {
          qAnimationEnergy.classList.remove("is-arming");
        }
        clearQuestionAnimationChargeState();
        clearQuestionAnimationDischargeState();
        restoreQuestionAnimationControlVisuals();
      };

      const runQuestionInitialBootIntro = (onDone) => {
        const bootToken = ++questionIntroBootToken;
        const finish = () => {
          if (bootToken !== questionIntroBootToken) {
            return;
          }
          questionIntroBootTimer = 0;
          if (stageNode) {
            stageNode.classList.remove("is-question-intro-booting");
          }
          if (qAnimationToggle) {
            qAnimationToggle.classList.remove("is-arming");
          }
          if (qAnimationEnergy) {
            qAnimationEnergy.classList.remove("is-arming");
          }
          clearQuestionAnimationChargeState();
          restoreQuestionAnimationControlVisuals();
          if (typeof onDone === "function") {
            onDone();
          }
        };
        if (!stageNode || !questionModeActive || (!qAnimationToggle && !qAnimationEnergy)) {
          finish();
          return;
        }
        if (questionIntroBootTimer) {
          window.clearTimeout(questionIntroBootTimer);
          questionIntroBootTimer = 0;
        }
        if (questionAnimationChargeTimer) {
          window.clearTimeout(questionAnimationChargeTimer);
          questionAnimationChargeTimer = 0;
        }
        if (questionAnimationRebootTimer) {
          window.clearTimeout(questionAnimationRebootTimer);
          questionAnimationRebootTimer = 0;
        }
        clearQuestionAnimationChargeState();
        stageNode.classList.add("is-question-intro-booting");
        stageNode.classList.remove("is-question-idle-static");
        setQuestionRevealAnimationsActive(true);
        if (qAnimationToggle) {
          qAnimationToggle.classList.remove("is-off", "is-on", "is-arming");
          void qAnimationToggle.offsetWidth;
          qAnimationToggle.classList.add("is-on", "is-arming");
          const animationLabel = qAnimationToggle.querySelector(".ft-q-animation-label");
          if (animationLabel) {
            animationLabel.textContent = "Anim on";
          }
          qAnimationToggle.setAttribute("aria-pressed", "false");
        }
        if (qAnimationEnergy) {
          qAnimationEnergy.classList.remove("is-off", "is-on", "is-arming");
          void qAnimationEnergy.offsetWidth;
          qAnimationEnergy.classList.add("is-on", "is-arming");
        }
        setQuestionFeedback("Booting question root...", "ok");
        questionIntroBootTimer = window.setTimeout(() => {
          questionIntroBootTimer = 0;
          if (bootToken !== questionIntroBootToken || !questionModeActive) {
            return;
          }
          setQuestionAnimationChargeState();
          questionIntroBootTimer = window.setTimeout(finish, QUESTION_ANIMATION_ENERGY_SHOCK_MS + 220);
        }, questionAnimationEnergyChargeDuration());
      };

      const triggerQuestionAnimationReboot = () => {
        if (!stageNode || !questionModeActive) {
          return;
        }
        const rebootToken = ++questionAnimationRebootToken;
        if (questionAnimationRebootTimer) {
          window.clearTimeout(questionAnimationRebootTimer);
          questionAnimationRebootTimer = 0;
        }
        if (questionAnimationChargeTimer) {
          window.clearTimeout(questionAnimationChargeTimer);
          questionAnimationChargeTimer = 0;
        }
        clearQuestionAnimationChargeState();
        if (qAnimationToggle) {
          qAnimationToggle.classList.remove("is-arming");
          void qAnimationToggle.offsetWidth;
          qAnimationToggle.classList.add("is-arming");
        }
        if (qAnimationEnergy) {
          qAnimationEnergy.classList.remove("is-arming");
          void qAnimationEnergy.offsetWidth;
          qAnimationEnergy.classList.add("is-arming");
        }
        stageNode.classList.remove("is-question-animation-rebooting");
        stageNode.classList.remove("is-question-picture-replay-resetting");
        clearQuestionRebootPhaseClasses();
        stageNode.classList.add("is-question-reboot-staging");
        stageNode.classList.remove("is-question-idle-static");
        const startPictureReboot = () => {
          if (!isQuestionAnimationRebootCurrent(rebootToken)) {
            return;
          }
          stageNode.classList.add("is-question-picture-replay-resetting");
          if (qPictureCard) {
            void qPictureCard.offsetWidth;
          } else {
            void stageNode.offsetWidth;
          }
          stageNode.classList.remove("is-question-picture-replay-resetting");
          pulseQuestionRebootCards();
          stageNode.classList.add("is-question-animation-rebooting");
          window.setTimeout(() => {
            if (
              !stageNode
              || rebootToken !== questionAnimationRebootToken
              || questionAnimationsPaused
              || !stageNode.classList.contains("is-question-animation-rebooting")
              || !isQuestionPictureRegionPromptPinned()
              || !questionRootInfoCard
              || !questionRootInfoCard.classList.contains("is-live")
            ) {
              return;
            }
            if (qQuestionCard && isQuestionCardInLayout(qQuestionCard)) {
              keepQuestionCardOnlyInView({ passes: 2 });
              return;
            }
            panQuestionCameraTo(questionRootInfoCard, () => settleQuestionCameraFocus(questionRootInfoCard, null, 2), 760);
          }, 3260);
          queueQuestionRebootPhase("is-question-reboot-regions", 1980, rebootToken);
          queueQuestionRebootPhase("is-question-reboot-rails", 2640, rebootToken);
          queueQuestionRebootPhase("is-question-reboot-prompt", 3220, rebootToken);
          queueQuestionRebootPhase("is-question-reboot-answers", 3560, rebootToken);
          queueQuestionRebootPhase("is-question-reboot-electrons", 3740, rebootToken);
          questionAnimationRebootTimer = window.setTimeout(() => {
            questionAnimationRebootTimer = 0;
            if (stageNode && rebootToken === questionAnimationRebootToken) {
              stageNode.classList.remove("is-question-animation-rebooting");
              stageNode.classList.remove("is-question-reboot-staging");
              clearQuestionRebootPhaseClasses();
            }
            if (qAnimationToggle) {
              qAnimationToggle.classList.remove("is-arming");
            }
            if (qAnimationEnergy) {
              qAnimationEnergy.classList.remove("is-arming");
            }
            clearQuestionAnimationChargeState();
            updateQuestionIdleStaticState();
          }, 5400);
        };
        const focusPictureThenReboot = () => {
          if (!isQuestionAnimationRebootCurrent(rebootToken)) {
            return;
          }
          const pictureTarget = qPictureCard && qPictureCard.classList.contains("is-live")
            ? qPictureCard
            : null;
          if (pictureTarget) {
            panQuestionAnimationRebootTo(pictureTarget, rebootToken, startPictureReboot, 760);
          } else {
            startPictureReboot();
          }
        };
        const focusAudioThenPicture = () => {
          if (!isQuestionAnimationRebootCurrent(rebootToken)) {
            return;
          }
          const audioTarget = qAudioCard && qAudioCard.classList.contains("is-live")
            ? qAudioCard
            : null;
          if (audioTarget) {
            panQuestionAnimationRebootTo(audioTarget, rebootToken, () => {
              pulseQuestionRebootCards([audioTarget]);
              activateQuestionCardFx(audioTarget, 1800);
              window.setTimeout(focusPictureThenReboot, 560);
            }, 720);
          } else {
            focusPictureThenReboot();
          }
        };
        questionAnimationChargeTimer = window.setTimeout(() => {
          questionAnimationChargeTimer = 0;
          if (!isQuestionAnimationRebootCurrent(rebootToken)) {
            return;
          }
          setQuestionAnimationChargeState();
          questionAnimationChargeTimer = window.setTimeout(() => {
            questionAnimationChargeTimer = 0;
            clearQuestionAnimationChargeState();
            focusAudioThenPicture();
          }, QUESTION_ANIMATION_ENERGY_SHOCK_MS);
        }, questionAnimationEnergyChargeDuration());
      };

      const applyQuestionSideCardsPreference = (options = {}) => {
        const paused = Boolean(questionCardEffectsPaused);
        if (qSideCardToggle) {
          qSideCardToggle.classList.toggle("is-off", paused);
          qSideCardToggle.textContent = paused ? "FX off" : "FX on";
          qSideCardToggle.setAttribute("aria-pressed", paused ? "true" : "false");
          qSideCardToggle.title = paused ? "Only animate the focused card" : "Animate all Space_Q cards";
        }
        if (qRootCard) {
          qRootCard.classList.toggle("is-card-effects-paused", paused);
        }
        if (stageNode) {
          stageNode.classList.toggle("is-question-effects-paused", paused);
        }
        if (paused) {
          window.requestAnimationFrame(() => {
            if (!questionCardEffectsPaused) {
              return;
            }
            if (typeof stopSpaceNavigatorMotion === "function") {
              stopSpaceNavigatorMotion();
            }
            if (typeof stopSpaceKeyboardNavigation === "function") {
              stopSpaceKeyboardNavigation();
            }
          });
        }
        updateQuestionIdleStaticState();
        if (options && options.render === false) {
          return;
        }
        if (questionModeActive && questionCurrentNode) {
          if (isQuestionPictureRegionPromptPinned()) {
            settleQuestionPictureRegionPrompt();
          } else {
            renderQuestionSideCards(questionCurrentNode);
          }
        }
        scheduleQuestionSideLayout();
      };

      function updateQuestionIdleStaticState() {
        if (!stageNode) {
          return;
        }
        const idleStatic = Boolean(
          questionModeActive
          && questionCardsRevealSettled
          && !questionRevealAnimationsActive
          && (questionAnimationsPaused || questionCardEffectsPaused)
        );
        stageNode.classList.toggle("is-question-idle-static", idleStatic);
      }

      const setQuestionRevealAnimationsActive = (active) => {
        questionRevealAnimationsActive = Boolean(active);
        if (stageNode) {
          stageNode.classList.toggle("is-question-reveal-animating", questionRevealAnimationsActive);
        }
        updateQuestionIdleStaticState();
      };

      const isQuestionMobilePerformanceSurface = () => window.matchMedia("(max-width: 900px), (pointer: coarse)").matches;

      const endQuestionMobileLoadSmoothing = () => {
        if (questionMobileLoadSmoothingTimer) {
          window.clearTimeout(questionMobileLoadSmoothingTimer);
          questionMobileLoadSmoothingTimer = 0;
        }
        if (stageNode) {
          stageNode.classList.remove("is-question-mobile-loading");
        }
      };

      const beginQuestionMobileLoadSmoothing = (durationMs = 3200) => {
        if (!isQuestionMobilePerformanceSurface()) {
          endQuestionMobileLoadSmoothing();
          return;
        }
        if (stageNode) {
          stageNode.classList.add("is-question-mobile-loading");
        }
        if (questionMobileLoadSmoothingTimer) {
          window.clearTimeout(questionMobileLoadSmoothingTimer);
        }
        questionMobileLoadSmoothingTimer = window.setTimeout(() => {
          questionMobileLoadSmoothingTimer = 0;
          if (!questionModeActive || questionCardsRevealSettled) {
            endQuestionMobileLoadSmoothing();
          }
        }, Math.max(900, Number(durationMs) || 3200));
      };

      const syncQuestionSideCardsSettingsToServer = async () => {
        if (!authToken) {
          return;
        }
        try {
          await fetchAuthJson("/auth/preferences", {
            method: "POST",
            body: JSON.stringify({
              question_motion: questionMotionSettings,
              question_animation: {
                paused: Boolean(questionAnimationsPaused),
                enabled: !questionAnimationsPaused,
              },
              question_side_cards: {
                effects_paused: Boolean(questionCardEffectsPaused),
                hidden: Boolean(questionCardEffectsPaused),
              },
            }),
          });
        } catch (error) {
          // Local storage remains the offline fallback.
        }
      };

      const syncQuestionAnimationSettingsToServer = async (pausedOverride = null) => {
        if (!authToken) {
          return;
        }
        const paused = pausedOverride === null || pausedOverride === undefined
          ? Boolean(questionAnimationsPaused)
          : Boolean(pausedOverride);
        try {
          await fetchAuthJson("/auth/preferences", {
            method: "POST",
            body: JSON.stringify({
              question_motion: questionMotionSettings,
              question_animation: {
                paused,
                enabled: !paused,
              },
              question_side_cards: {
                effects_paused: Boolean(questionCardEffectsPaused),
                hidden: Boolean(questionCardEffectsPaused),
              },
            }),
          });
        } catch (error) {
          // Local storage remains the offline fallback.
        }
      };

      const toggleQuestionSideCards = () => {
        questionCardEffectsPaused = !questionCardEffectsPaused;
        saveQuestionSideCardsSettings();
        applyQuestionSideCardsPreference();
        void syncQuestionSideCardsSettingsToServer();
      };

      const toggleQuestionAnimation = () => {
        if (questionRevealAnimationOverrideActive) {
          questionRevealAnimationRestorePaused = !questionRevealAnimationRestorePaused;
          saveQuestionAnimationSettings(questionRevealAnimationRestorePaused);
          setQuestionAnimationControlVisualOn();
          void syncQuestionAnimationSettingsToServer(questionRevealAnimationRestorePaused);
          return;
        }
        const wasPaused = Boolean(questionAnimationsPaused);
        questionAnimationsPaused = !questionAnimationsPaused;
        saveQuestionAnimationSettings();
        applyQuestionAnimationPreference({ discharge: !wasPaused && questionAnimationsPaused });
        if (wasPaused && !questionAnimationsPaused) {
          if (questionCardEffectsPaused) {
            questionCardEffectsPaused = false;
            saveQuestionSideCardsSettings();
            applyQuestionSideCardsPreference({ render: false });
          }
          triggerQuestionAnimationReboot();
        }
        void syncQuestionAnimationSettingsToServer();
      };

      const toggleQuestionMotionSetting = (key) => {
        if (key !== "picture" && key !== "audio") {
          return;
        }
        questionMotionSettings[key] = normalizeQuestionMotionMode(questionMotionSettings[key]) === "always" ? "hover" : "always";
        saveQuestionMotionSettings();
        applyQuestionMotionSettings();
        void syncQuestionMotionSettingsToServer();
      };

      loadQuestionMotionSettings();
      loadQuestionSideCardsSettings();
      loadQuestionAnimationSettings();
      applyQuestionMotionSettings();
      applyQuestionSideCardsPreference({ render: false });
      applyQuestionAnimationPreference();

      function normalizeTaskNoticeProfilePayload(payload = {}) {
        const source = payload && typeof payload === "object" ? payload : {};
        const profile = source.task_notice_profile || source.taskNoticeProfile || source.notice_profile || {};
        const data = profile && typeof profile === "object" ? profile : {};
        return {
          speaker_name: clean(data.speaker_name || data.speakerName || data.name || ""),
          avatar: clean(data.avatar || data.avatar_url || data.avatarUrl || ""),
          notice_style: normalizeTaskNoticeStyle(data.notice_style || data.noticeStyle || data.style || "hologram"),
          active_language: clean(data.active_language || data.activeLanguage || data.language || "vi") === "en" ? "en" : "vi",
          draft_text: preserveQuestionText(data.draft_text || data.draftText || data.message || data.text || ""),
          draft_text_en: preserveQuestionText(data.draft_text_en || data.draftTextEn || data.english || ""),
          draft_text_vi: preserveQuestionText(data.draft_text_vi || data.draftTextVi || data.vietnamese || data.vi || ""),
        };
      }

      function applyTaskNoticeProfilePayload(payload = {}) {
        const profile = normalizeTaskNoticeProfilePayload(payload);
        taskNoticeProfile = {
          speaker_name: profile.speaker_name || taskNoticeProfile.speaker_name || "",
          avatar: profile.avatar || taskNoticeProfile.avatar || "",
          notice_style: normalizeTaskNoticeStyle(profile.notice_style || taskNoticeProfile.notice_style || "hologram"),
          active_language: profile.active_language || taskNoticeProfile.active_language || "vi",
          draft_text: preserveQuestionText(profile.draft_text),
          draft_text_en: preserveQuestionText(profile.draft_text_en || (profile.active_language === "en" ? profile.draft_text : "")),
          draft_text_vi: preserveQuestionText(profile.draft_text_vi || (profile.active_language !== "en" ? profile.draft_text : "")),
        };
        if (!taskNoticeEditId) {
          if (taskNoticeName && !clean(taskNoticeName.value)) {
            taskNoticeName.value = taskNoticeProfile.speaker_name;
          }
          if (taskNoticeAvatar && !clean(taskNoticeAvatar.value)) {
            taskNoticeAvatar.value = taskNoticeProfile.avatar;
          }
          if (taskNoticeStyle) {
            taskNoticeStyle.value = normalizeTaskNoticeStyle(taskNoticeProfile.notice_style || "hologram");
          }
          if (taskNoticeLanguage) {
            taskNoticeLanguage.value = taskNoticeProfile.active_language === "en" ? "en" : "vi";
          }
          if (taskNoticeTextEn && !preserveQuestionText(taskNoticeTextEn.value)) {
            taskNoticeTextEn.value = taskNoticeProfile.draft_text_en || "";
          }
          if (taskNoticeTextVi && !preserveQuestionText(taskNoticeTextVi.value)) {
            taskNoticeTextVi.value = taskNoticeProfile.draft_text_vi || taskNoticeProfile.draft_text || "";
          }
        }
      }

      function currentTaskNoticeProfilePayload() {
        const activeLanguage = taskNoticeLanguage && taskNoticeLanguage.value === "en" ? "en" : "vi";
        const draftEn = preserveQuestionText(taskNoticeTextEn ? taskNoticeTextEn.value : taskNoticeProfile.draft_text_en);
        const draftVi = preserveQuestionText(taskNoticeTextVi ? taskNoticeTextVi.value : taskNoticeProfile.draft_text_vi);
        return {
          speaker_name: clean(taskNoticeName ? taskNoticeName.value : taskNoticeProfile.speaker_name),
          avatar: clean(taskNoticeAvatar ? taskNoticeAvatar.value : taskNoticeProfile.avatar),
          notice_style: normalizeTaskNoticeStyle(taskNoticeStyle ? taskNoticeStyle.value : taskNoticeProfile.notice_style),
          active_language: activeLanguage,
          draft_text: activeLanguage === "en" ? draftEn : draftVi,
          draft_text_en: draftEn,
          draft_text_vi: draftVi,
        };
      }

      async function syncTaskNoticeProfilePreference() {
        if (!authToken || !currentAuthIsAdmin) {
          return;
        }
        const profile = currentTaskNoticeProfilePayload();
        taskNoticeProfile = profile;
        try {
          await fetchAuthJson("/auth/preferences", {
            method: "POST",
            body: JSON.stringify({ task_notice_profile: profile }),
          });
        } catch (error) {
        }
      }

      function scheduleTaskNoticeProfilePreferenceSync(delayMs = 500) {
        taskNoticeProfile = currentTaskNoticeProfilePayload();
        if (taskNoticeProfileSyncTimer) {
          window.clearTimeout(taskNoticeProfileSyncTimer);
        }
        const wait = Math.max(0, Number(delayMs) || 0);
        taskNoticeProfileSyncTimer = window.setTimeout(() => {
          taskNoticeProfileSyncTimer = 0;
          void syncTaskNoticeProfilePreference();
        }, wait);
      }

      const authProfileAvatarPath = (profile = {}) => {
        const data = profile && typeof profile === "object" ? profile : {};
        return clean(data.avatar || data.avatar_url || data.avatarUrl || data.picture || data.picture_url || data.pictureUrl || "");
      };

      const authGenderFor = (profile = {}) => {
        const gender = clean(profile && (profile.gender || profile.sex || "")).toLowerCase();
        return ["male", "female", "other"].includes(gender) ? gender : "other";
      };

      const normalizeProfilePhotos = (value = []) => (Array.isArray(value) ? value : [])
        .map((item) => {
          if (item && typeof item === "object") {
            return clean(item.path || item.photo || item.url || item.src || "");
          }
          return clean(item || "");
        })
        .filter(Boolean)
        .slice(0, 4);

      const profileAvatarDefaultMarkup = () => `
        <svg viewBox="0 0 64 64" focusable="false" aria-hidden="true">
          <path class="avatar-hair" d="M17 31c0-11 6.4-19 15-19s15 8 15 19c0 9-3.3 17-15 17S17 40 17 31Z" fill="currentColor" opacity=".18"/>
          <path d="M18.5 50c2.5-8.8 8.1-13 13.5-13s11 4.2 13.5 13" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
          <path d="M22 27c0-7.3 4.3-12.4 10-12.4S42 19.7 42 27s-4.3 12.4-10 12.4S22 34.3 22 27Z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
          <path class="avatar-jaw" d="M22.5 25.5c5.7-2.7 13.3-2.7 19 0" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" opacity=".62"/>
        </svg>`;

      const profileDisplayName = (profile = {}) => clean(
        profile.display_name || profile.displayName || profile.full_name || profile.fullName || profile.username || "Learner"
      );

      const renderProfileAvatar = (container, profile = {}) => {
        if (!container) {
          return;
        }
        container.innerHTML = "";
        const avatar = authProfileAvatarPath(profile);
        if (avatar) {
          const img = document.createElement("img");
          img.alt = "";
          img.src = resolveServerAssetUrl(avatar);
          img.addEventListener("error", () => {
            container.innerHTML = profileAvatarDefaultMarkup();
          }, { once: true });
          container.appendChild(img);
        } else {
          container.innerHTML = profileAvatarDefaultMarkup();
        }
      };

      const renderPublicProfileCard = (profile = {}) => {
        if (profileNameNode) {
          profileNameNode.textContent = profileDisplayName(profile);
        }
        if (profileUserNode) {
          profileUserNode.textContent = clean(profile.username) ? `@${clean(profile.username)}` : "@learner";
        }
        renderProfileAvatar(profileAvatarNode, profile);
        if (profileIntroNode) {
          profileIntroNode.textContent = clean(profile.intro || profile.bio || profile.about || "") || "No introduction yet.";
        }
        if (profileGalleryNode) {
          profileGalleryNode.innerHTML = "";
          const photos = normalizeProfilePhotos(profile.profile_photos || profile.photos || profile.gallery || []);
          for (let index = 0; index < 4; index += 1) {
            const slot = document.createElement("div");
            slot.className = "ft-profile-photo";
            const photo = photos[index] || "";
            if (photo) {
              const img = document.createElement("img");
              img.alt = "";
              img.src = resolveServerAssetUrl(photo);
              img.addEventListener("error", () => {
                slot.classList.add("is-empty");
                slot.textContent = "No image";
              }, { once: true });
              slot.appendChild(img);
            } else {
              slot.classList.add("is-empty");
              slot.textContent = "No image";
            }
            profileGalleryNode.appendChild(slot);
          }
        }
      };

      const closePublicProfileCard = () => {
        if (!profileModal) {
          return;
        }
        profileModal.classList.remove("is-open");
        profileModal.setAttribute("aria-hidden", "true");
      };

      const openPublicProfileCard = async (username = "") => {
        const safeUsername = clean(username || currentAuthUsername);
        if (!safeUsername || !profileModal) {
          return;
        }
        profileModal.classList.add("is-open");
        profileModal.setAttribute("aria-hidden", "false");
        renderPublicProfileCard({ username: safeUsername, display_name: "Loading profile..." });
        try {
          const cacheKey = safeUsername.toLowerCase();
          let cached = publicProfileCache.get(cacheKey);
          let profile = cached && Date.now() - Number(cached.at || 0) < 120000 ? cached.profile : null;
          if (!profile) {
            const result = await fetchAuthJson(`/profile/public?username=${encodeURIComponent(safeUsername)}`);
            profile = result.payload && result.payload.profile ? result.payload.profile : {};
            publicProfileCache.set(cacheKey, { profile, at: Date.now() });
          }
          renderPublicProfileCard(profile);
        } catch (error) {
          renderPublicProfileCard({
            username: safeUsername,
            display_name: safeUsername,
            intro: error && error.message ? error.message : "Could not load profile.",
          });
        }
      };

      const renderProfileEditSlots = () => {
        if (!profileEditGallery) {
          return;
        }
        profileEditGallery.innerHTML = "";
        for (let index = 0; index < 4; index += 1) {
          const photo = profileEditPhotos[index] || "";
          const slot = document.createElement("div");
          slot.className = `ft-profile-edit-slot ${photo ? "" : "is-empty"}`;
          if (photo) {
            const img = document.createElement("img");
            img.alt = "";
            img.src = resolveServerAssetUrl(photo);
            img.addEventListener("error", () => {
              slot.classList.add("is-empty");
            }, { once: true });
            slot.appendChild(img);
          } else {
            slot.textContent = `Photo ${index + 1}`;
          }
          const actions = document.createElement("div");
          actions.className = "ft-profile-edit-slot-actions";
          const upload = document.createElement("button");
          upload.type = "button";
          upload.textContent = photo ? "Replace" : "Upload";
          upload.addEventListener("click", () => {
            profileEditUploadSlot = index;
            if (profilePhotoFileInput) {
              profilePhotoFileInput.click();
            }
          });
          const remove = document.createElement("button");
          remove.type = "button";
          remove.textContent = "Remove";
          remove.disabled = !photo;
          remove.addEventListener("click", () => {
            profileEditPhotos[index] = "";
            profileEditPhotos = normalizeProfilePhotos(profileEditPhotos);
            renderProfileEditSlots();
            if (profileEditStatus) {
              profileEditStatus.textContent = "Photo removed. Save card to sync.";
            }
          });
          actions.append(upload, remove);
          slot.appendChild(actions);
          profileEditGallery.appendChild(slot);
        }
      };

      const openProfileEditCard = () => {
        if (!profileEditModal) {
          return;
        }
        profileEditPhotos = normalizeProfilePhotos(currentAuthProfile.profile_photos || currentAuthProfile.photos || currentAuthProfile.gallery || []);
        if (profileEditEmail) {
          profileEditEmail.value = clean(currentAuthProfile.email || currentAuthProfile.gmail || "");
        }
        if (profileEditIntro) {
          profileEditIntro.value = clean(currentAuthProfile.intro || currentAuthProfile.bio || currentAuthProfile.about || "");
        }
        renderProfileEditSlots();
        if (profileEditStatus) {
          profileEditStatus.textContent = "Add up to 4 profile photos.";
        }
        profileEditModal.classList.add("is-open");
        profileEditModal.setAttribute("aria-hidden", "false");
        if (userMenu) {
          userMenu.classList.remove("is-open");
        }
        if (userButton) {
          userButton.setAttribute("aria-expanded", "false");
        }
      };

      const closeProfileEditCard = () => {
        if (!profileEditModal) {
          return;
        }
        profileEditModal.classList.remove("is-open");
        profileEditModal.setAttribute("aria-hidden", "true");
      };

      const saveProfileEditCard = async () => {
        if (!authToken) {
          return;
        }
        if (profileEditSave) {
          profileEditSave.disabled = true;
          profileEditSave.textContent = "Saving";
        }
        if (profileEditStatus) {
          profileEditStatus.textContent = "Saving public profile card...";
        }
        try {
          const recoveryEmail = clean(profileEditEmail && profileEditEmail.value || "");
          const profileResult = await fetchAuthJson("/auth/profile", {
            method: "POST",
            body: JSON.stringify({
              full_name: clean(currentAuthProfile.full_name || currentAuthProfile.fullName || currentAuthProfile.display_name || currentAuthUsername || ""),
              gender: clean(currentAuthProfile.gender || "other"),
              birth_date: clean(currentAuthProfile.birth_date || currentAuthProfile.birthDate || ""),
              email: recoveryEmail,
            }),
          });
          const savedProfilePayload = profileResult.payload || {};
          const savedProfile = savedProfilePayload.profile && typeof savedProfilePayload.profile === "object" ? savedProfilePayload.profile : {};
          const result = await fetchAuthJson("/auth/profile-card", {
            method: "POST",
            body: JSON.stringify({
              intro: profileEditIntro ? profileEditIntro.value : "",
              profile_photos: normalizeProfilePhotos(profileEditPhotos),
            }),
          });
          const payload = result.payload || {};
          const profile = payload.profile && typeof payload.profile === "object" ? payload.profile : payload.profile_card || {};
          currentAuthProfile = { ...currentAuthProfile, ...savedProfile, ...profile };
          profileEditPhotos = normalizeProfilePhotos(currentAuthProfile.profile_photos || []);
          publicProfileCache.delete(clean(currentAuthUsername).toLowerCase());
          renderProfileEditSlots();
          if (profileEditStatus) {
            profileEditStatus.textContent = "Profile card synced.";
          }
        } catch (error) {
          if (profileEditStatus) {
            profileEditStatus.textContent = error && error.message ? error.message : "Could not save profile card.";
          }
        } finally {
          if (profileEditSave) {
            profileEditSave.disabled = false;
            profileEditSave.textContent = "Save card";
          }
        }
      };

      const uploadProfileEditPhoto = async (file) => {
        if (!file || !authToken) {
          return;
        }
        if (profileEditStatus) {
          profileEditStatus.textContent = "Processing profile photo...";
        }
        try {
          const form = new FormData();
          form.append("file", file);
          form.append("slot", String(Math.max(0, Math.min(3, profileEditUploadSlot))));
          const result = await fetchAuthForm("/auth/profile-photo", form);
          const payload = result.payload || {};
          const profile = payload.profile && typeof payload.profile === "object" ? payload.profile : {};
          currentAuthProfile = { ...currentAuthProfile, ...profile };
          profileEditPhotos = normalizeProfilePhotos(currentAuthProfile.profile_photos || []);
          publicProfileCache.delete(clean(currentAuthUsername).toLowerCase());
          renderProfileEditSlots();
          if (profileEditStatus) {
            const kb = Math.max(1, Math.round(Number(payload.bytes || 0) / 1024));
            profileEditStatus.textContent = `Photo synced (${kb} KB).`;
          }
        } catch (error) {
          if (profileEditStatus) {
            profileEditStatus.textContent = error && error.message ? error.message : "Could not upload profile photo.";
          }
        } finally {
          profileEditUploadSlot = -1;
          if (profilePhotoFileInput) {
            profilePhotoFileInput.value = "";
          }
        }
      };

      const setUserAvatarNodes = (profile = {}, username = currentAuthUsername, options = {}) => {
        const renderProfile = profile && typeof profile === "object" ? profile : {};
        if (!options || !options.preview) {
          currentAuthProfile = renderProfile ? { ...currentAuthProfile, ...renderProfile } : currentAuthProfile;
        }
        const sourceProfile = options && options.preview ? renderProfile : currentAuthProfile;
        const avatarPath = authProfileAvatarPath(sourceProfile);
        const avatarUrl = avatarPath ? resolveServerAssetUrl(avatarPath) : "";
        const gender = authGenderFor(sourceProfile);
        [
          [userAvatar, userAvatarImg],
          [userMenuAvatar, userMenuAvatarImg],
        ].forEach(([wrap, img]) => {
          if (!wrap || !img) return;
          wrap.classList.remove("is-male", "is-female", "is-other");
          wrap.classList.add(`is-${gender}`);
          wrap.classList.toggle("has-image", Boolean(avatarUrl));
          if (avatarUrl) {
            img.src = avatarUrl;
          } else {
            img.removeAttribute("src");
          }
        });
      };

      const activeWorldUsername = () => clean(activeNpcActor && activeNpcActor.username ? activeNpcActor.username : currentAuthUsername);

      const activeWorldActorPayload = () => {
        const actor = activeWorldUsername();
        return actor && actor !== clean(currentAuthUsername) ? { actor } : {};
      };

      const activeWorldActorQuery = (prefix = "?") => {
        const actor = clean(activeWorldActorPayload().actor || "");
        return actor ? `${prefix}actor=${encodeURIComponent(actor)}` : "";
      };

      const renderActiveUserIdentity = () => {
        const isNpc = Boolean(activeNpcActor && activeNpcActor.username);
        const actor = isNpc ? activeNpcActor : null;
        const profile = isNpc
          ? {
              full_name: clean(actor.display_name || actor.displayName || actor.username),
              avatar: clean(actor.avatar || ""),
              gender: clean(actor.gender || "other"),
            }
          : currentAuthProfile;
        const username = isNpc ? clean(actor.username) : clean(currentAuthUsername);
        if (userNameNode) {
          userNameNode.textContent = isNpc ? (clean(actor.display_name || actor.displayName) || username) : (username || "User");
        }
        if (userMenuName) {
          if (isNpc) {
            const alias = clean(actor.login_alias || actor.loginAlias || "");
            userMenuName.textContent = `Acting as: ${clean(actor.display_name || actor.displayName || username)}${alias ? ` | ${alias}` : ""}`;
          } else {
            const fullName = clean(currentAuthProfile.full_name || currentAuthProfile.fullName || "");
            userMenuName.textContent = username ? (fullName ? `${fullName} | @${username}` : `Signed in: ${username}`) : "Sign in";
          }
        }
        if (userAvatarStatus) {
          userAvatarStatus.textContent = isNpc ? "NPC actor active for QM-City." : (authProfileAvatarPath(currentAuthProfile) ? "Avatar synced." : "No avatar yet.");
        }
        if (npcSwitchButton) {
          npcSwitchButton.classList.toggle("is-acting", isNpc);
          npcSwitchButton.title = isNpc ? `Acting as ${clean(actor.display_name || actor.displayName || username)}` : "Switch admin NPC racer";
        }
        setUserAvatarNodes(profile, username, { preview: isNpc });
      };

      const normalizePdfAdminActingUser = (value = "") => {
        const username = clean(value).toLowerCase();
        if (!username || username === clean(currentAuthUsername).toLowerCase()) {
          return "";
        }
        return username;
      };

      const pdfDrawingOwnerUsername = () => normalizePdfAdminActingUser(pdfAdminActingUser) || clean(currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase() || "guest";

      const setPdfAdminUserStatus = (message = "") => {
        if (pdfAdminUserStatus) {
          pdfAdminUserStatus.textContent = clean(message) || "Saving for your account.";
        }
        if (pdfAdminUserNote) {
          const owner = pdfDrawingOwnerUsername();
          const admin = clean(currentAuthUsername).toLowerCase();
          pdfAdminUserNote.textContent = currentAuthIsAdmin && pdfAdminActingUser
            ? `PDF/Picture drawings are loading and saving as @${owner}.`
            : (currentAuthIsAdmin ? "Choose a learner to load and save their PDF/Picture drawings." : "Open Space_PDF or Space_Picture to switch the saved drawing owner.");
          pdfAdminUserNote.classList.toggle("is-active", Boolean(currentAuthIsAdmin && pdfAdminActingUser && owner !== admin));
        }
      };

      const renderPdfAdminUserOptions = () => {
        if (!pdfAdminUserSelect) {
          return;
        }
        const selected = normalizePdfAdminActingUser(pdfAdminActingUser);
        pdfAdminUserSelect.replaceChildren();
        const own = document.createElement("option");
        own.value = "";
        own.textContent = `Admin account (${clean(currentAuthUsername) || "me"})`;
        pdfAdminUserSelect.appendChild(own);
        const seen = new Set([clean(currentAuthUsername).toLowerCase()]);
        (Array.isArray(pdfAdminUserRows) ? pdfAdminUserRows : []).forEach((row) => {
          const username = clean(row && row.username).toLowerCase();
          if (!username || seen.has(username)) {
            return;
          }
          seen.add(username);
          const option = document.createElement("option");
          option.value = username;
          const fullName = clean(row.full_name || row.fullName || "");
          option.textContent = fullName ? `${fullName} (@${username})` : `@${username}`;
          pdfAdminUserSelect.appendChild(option);
        });
        pdfAdminUserSelect.value = selected;
      };

      const resetPdfAdminActingUserState = (options = {}) => {
        const clearUsers = !Object.prototype.hasOwnProperty.call(options, "clearUsers") || Boolean(options.clearUsers);
        pdfAdminActingUser = "";
        pdfAdminUserBusy = false;
        if (clearUsers) {
          pdfAdminUserRows = [];
          pdfAdminUsersLoadedAt = 0;
        }
        if (pdfAdminUserPanel) {
          pdfAdminUserPanel.hidden = true;
        }
        try {
          localStorage.removeItem(PDF_ADMIN_ACTING_USER_KEY);
        } catch (error) {
        }
        renderPdfAdminUserOptions();
        setPdfAdminUserStatus("Saving for admin account.");
      };

      const syncPdfAdminUserControls = () => {
        const show = Boolean(currentAuthIsAdmin && typeof pdfModeActive !== "undefined" && pdfModeActive);
        if (pdfAdminUserOpenButton) {
          pdfAdminUserOpenButton.hidden = !show;
        }
        if (!show && pdfAdminUserPanel) {
          pdfAdminUserPanel.hidden = true;
        }
        if (!currentAuthIsAdmin) {
          resetPdfAdminActingUserState();
          return;
        }
        renderPdfAdminUserOptions();
        const target = normalizePdfAdminActingUser(pdfAdminActingUser);
        setPdfAdminUserStatus(target ? `Acting as @${target}` : "Saving for admin account.");
      };

      const loadPdfAdminUsers = async (options = {}) => {
        if (!currentAuthIsAdmin || !(typeof pdfModeActive !== "undefined" && pdfModeActive) || pdfAdminUserBusy) {
          return pdfAdminUserRows;
        }
        const fresh = Boolean(options.fresh);
        if (!fresh && pdfAdminUserRows.length && Date.now() - Number(pdfAdminUsersLoadedAt || 0) < 60000) {
          renderPdfAdminUserOptions();
          return pdfAdminUserRows;
        }
        pdfAdminUserBusy = true;
        setPdfAdminUserStatus("Loading users...");
        try {
          const { payload } = await fetchAuthJson("/auth/admin-users");
          pdfAdminUserRows = Array.isArray(payload && payload.users) ? payload.users : [];
          pdfAdminUsersLoadedAt = Date.now();
          renderPdfAdminUserOptions();
          setPdfAdminUserStatus(pdfAdminActingUser ? `Acting as @${pdfAdminActingUser}` : "Choose learner.");
        } catch (error) {
          setPdfAdminUserStatus(error && error.message ? error.message : "Could not load users.");
        } finally {
          pdfAdminUserBusy = false;
        }
        return pdfAdminUserRows;
      };

      const applyPdfAdminActingUser = async (username = "") => {
        if (!currentAuthIsAdmin) {
          return;
        }
        const nextUser = normalizePdfAdminActingUser(username);
        if (pdfModeActive && pdfState && pdfState.path) {
          await Promise.allSettled([
            typeof savePdfDrawingLayer === "function" ? savePdfDrawingLayer() : Promise.resolve(),
            typeof savePdfProgressNow === "function" ? savePdfProgressNow() : Promise.resolve(),
          ]);
        }
        pdfAdminActingUser = nextUser;
        try {
          if (nextUser) {
            localStorage.setItem(PDF_ADMIN_ACTING_USER_KEY, nextUser);
          } else {
            localStorage.removeItem(PDF_ADMIN_ACTING_USER_KEY);
          }
        } catch (error) {
        }
        syncPdfAdminUserControls();
        if (pdfModeActive && pdfState && pdfState.path && typeof reloadPdfCurrentDocumentForViewer === "function") {
          setPdfAdminUserStatus(nextUser ? `Opening @${nextUser}...` : "Opening admin account...");
          await reloadPdfCurrentDocumentForViewer({
            statusMessage: nextUser
              ? `Admin is opening this PDF/Picture as @${nextUser}.`
              : "Admin is opening this PDF/Picture as admin.",
          });
        }
      };

      const setActiveNpcActor = (actor = null) => {
        activeNpcActor = actor && actor.username ? { ...actor } : null;
        renderActiveUserIdentity();
        if (worldModal && worldModal.classList.contains("is-open")) {
          sharedWorldRoster.clear();
          sharedWorldNodes.forEach((node) => node.remove());
          sharedWorldNodes.clear();
          void refreshSharedWorld();
        }
      };

      const npcSwitchGenderSymbol = (gender = "") => {
        const key = clean(gender).toLowerCase();
        if (key === "female") return "♀︎";
        if (key === "male") return "♂︎";
        return "◇︎";
      };

      const setNpcSwitchStatus = (message = "") => {
        if (npcSwitchStatus) {
          npcSwitchStatus.textContent = message || "Choose an NPC identity for QM-City and world chat.";
        }
      };

      const setNpcSwitchOpen = (open) => {
        if (!npcSwitchModal) {
          return;
        }
        const active = Boolean(open);
        npcSwitchModal.classList.toggle("is-open", active);
        npcSwitchModal.setAttribute("aria-hidden", active ? "false" : "true");
      };

      const renderNpcSwitchRoster = () => {
        if (!npcSwitchList) {
          return;
        }
        npcSwitchList.innerHTML = "";
        if (!npcSwitchRoster.length) {
          const empty = document.createElement("div");
          empty.className = "ft-npc-switch-status";
          empty.textContent = "No valid NPC image found in C:\\server data\\NPC_TOP.";
          npcSwitchList.append(empty);
          return;
        }
        npcSwitchRoster.forEach((npc) => {
          const row = document.createElement("button");
          row.type = "button";
          row.className = "ft-npc-switch-row";
          row.classList.toggle("is-active", Boolean(activeNpcActor && clean(activeNpcActor.username).toLowerCase() === clean(npc.username).toLowerCase()));
          const avatar = document.createElement("span");
          avatar.className = "ft-npc-switch-avatar";
          const avatarPath = clean(npc.avatar || "");
          if (avatarPath) {
            const img = document.createElement("img");
            img.src = resolveServerAssetUrl(avatarPath);
            img.alt = "";
            avatar.append(img);
          } else {
            avatar.textContent = clean(npc.display_name || npc.username || "?").slice(0, 1).toUpperCase() || "?";
          }
          const meta = document.createElement("span");
          meta.className = "ft-npc-switch-meta";
          const title = document.createElement("strong");
          title.textContent = `${clean(npc.display_name || npc.displayName || npc.username)} ${npcSwitchGenderSymbol(npc.gender)}`;
          const detail = document.createElement("span");
          const level = npc.character_level && typeof npc.character_level === "object" ? npc.character_level : {};
          detail.textContent = `NPC ${clean(npc.stt || "") || clean(npc.username)} · Lv ${Math.max(1, Number(level.level || 1) || 1)} · ${Math.max(0, Number(npc.total_words || 0) || 0)} total`;
          meta.append(title, detail);
          row.append(avatar, meta);
          row.addEventListener("click", () => {
            setActiveNpcActor(npc);
            setNpcSwitchStatus(`Acting as ${clean(npc.display_name || npc.displayName || npc.username)}.`);
            renderNpcSwitchRoster();
            setNpcSwitchOpen(false);
            showTopNotice(`Acting as ${clean(npc.display_name || npc.displayName || npc.username)} in QM-City.`, "ok", { duration: 3000 });
          });
          npcSwitchList.append(row);
        });
      };

      const loadNpcSwitchRoster = async (force = false) => {
        if (!currentAuthIsAdmin || !authToken) {
          npcSwitchRoster = [];
          return [];
        }
        if (!force && npcSwitchRoster.length && Date.now() - npcSwitchRosterLoadedAt < 20000) {
          renderNpcSwitchRoster();
          return npcSwitchRoster;
        }
        setNpcSwitchStatus("Loading NPC racers...");
        const response = await fetchAuthJson("/vocab/leaderboard/npc-top", { timeoutMs: 0 });
        const payload = response.payload || {};
        npcSwitchRoster = Array.isArray(payload.npcs) ? payload.npcs : [];
        npcSwitchRosterLoadedAt = Date.now();
        renderNpcSwitchRoster();
        setNpcSwitchStatus(npcSwitchRoster.length ? "Choose an NPC identity for QM-City and world chat." : "No valid NPC racer image found.");
        return npcSwitchRoster;
      };

      const selectedNpcSwitchActor = () => {
        const activeName = clean(activeNpcActor && activeNpcActor.username).toLowerCase();
        if (activeName) {
          const match = npcSwitchRoster.find((npc) => clean(npc.username).toLowerCase() === activeName);
          if (match) return match;
          return activeNpcActor;
        }
        return npcSwitchRoster[0] || null;
      };

      const normalizeNpcBuffAmount = () => {
        const raw = Number(npcSwitchBuffInput ? npcSwitchBuffInput.value : 0);
        if (!Number.isFinite(raw)) return 0;
        return Math.max(0, Math.min(25, Math.floor(raw)));
      };

      const buffSelectedNpcRacer = async () => {
        const npc = selectedNpcSwitchActor();
        if (!npc || !clean(npc.username)) {
          setNpcSwitchStatus("Choose an NPC racer first.");
          return;
        }
        const amount = normalizeNpcBuffAmount();
        if (amount < 1 || amount > 25) {
          setNpcSwitchStatus("Buff amount must be from 1 to 25 words.");
          if (npcSwitchBuffInput) npcSwitchBuffInput.focus();
          return;
        }
        if (npcSwitchBuffAdd) npcSwitchBuffAdd.disabled = true;
        setNpcSwitchStatus(`Adding ${amount} word${amount === 1 ? "" : "s"} to ${clean(npc.display_name || npc.displayName || npc.username)}...`);
        try {
          const response = await fetchAuthJson("/vocab/leaderboard/npc-top/buff", {
            method: "POST",
            body: JSON.stringify({ username: clean(npc.username), amount }),
            timeoutMs: 0,
          });
          const payload = response.payload || {};
          const buff = payload.buff && typeof payload.buff === "object" ? payload.buff : {};
          npcSwitchRoster = Array.isArray(payload.npcs) ? payload.npcs : npcSwitchRoster;
          npcSwitchRosterLoadedAt = Date.now();
          const refreshed = npcSwitchRoster.find((item) => clean(item.username).toLowerCase() === clean(npc.username).toLowerCase());
          if (refreshed && activeNpcActor && clean(activeNpcActor.username).toLowerCase() === clean(npc.username).toLowerCase()) {
            activeNpcActor = { ...activeNpcActor, ...refreshed };
            renderActiveUserIdentity();
          }
          cupLeaderboardCache.at = 0;
          if (cupModal && cupModal.classList.contains("is-open")) {
            void loadCupLeaderboard(true);
          }
          renderNpcSwitchRoster();
          setNpcSwitchStatus(`Buffed ${Math.max(0, Number(buff.applied_words || 0) || 0)} word${Number(buff.applied_words || 0) === 1 ? "" : "s"} | day ${Math.max(0, Number(buff.day_words || 0) || 0)}/150 | total +${Math.max(0, Number(buff.total_increment || 0) || 0)}.`);
          showTopNotice(`NPC racer buffed: +${Math.max(0, Number(buff.applied_words || 0) || 0)} words today.`, "ok", { duration: 3000 });
        } catch (error) {
          setNpcSwitchStatus(error && error.message ? error.message : "Could not buff NPC racer.");
        } finally {
          if (npcSwitchBuffAdd) npcSwitchBuffAdd.disabled = false;
        }
      };

      const uploadCurrentUserAvatar = async (file) => {
        if (!file || !authToken) {
          return;
        }
        if (userAvatarStatus) {
          userAvatarStatus.textContent = "Compressing and uploading avatar...";
        }
        if (userAvatarUploadButton) {
          userAvatarUploadButton.disabled = true;
        }
        try {
          const form = new FormData();
          form.append("file", file);
          const result = await fetchAuthForm("/auth/avatar", form);
          const payload = result.payload || {};
          const profile = payload.profile && typeof payload.profile === "object" ? payload.profile : {};
          currentAuthProfile = { ...currentAuthProfile, ...profile };
          setUserAvatarNodes(currentAuthProfile, currentAuthUsername);
          renderActiveUserIdentity();
          publicProfileCache.delete(clean(currentAuthUsername).toLowerCase());
          cupLeaderboardCache.at = 0;
          if (cupModal && cupModal.classList.contains("is-open")) {
            void loadCupLeaderboard(true);
          }
          if (userAvatarStatus) {
            const kb = Math.max(1, Math.round(Number(payload.bytes || 0) / 1024));
            userAvatarStatus.textContent = `Avatar synced (${kb} KB).`;
          }
        } catch (error) {
          if (userAvatarStatus) {
            userAvatarStatus.textContent = error && error.message ? error.message : "Could not upload avatar.";
          }
        } finally {
          if (userAvatarUploadButton) {
            userAvatarUploadButton.disabled = false;
          }
          if (userAvatarFileInput) {
            userAvatarFileInput.value = "";
          }
        }
      };

      const completeAuth = async (payload = {}) => {
        const authTimelineNow = () => (typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now());
        const authPhaseStart = authTimelineNow();
        const authResponseCompletedAt = Date.now();
        let authPhaseMark = authPhaseStart;
        const recordAuthPhase = (phase = "") => {
          if (typeof window === "undefined" || typeof window.__ftRecordLoginTimelinePhase !== "function") {
            authPhaseMark = authTimelineNow();
            return;
          }
          const now = authTimelineNow();
          window.__ftRecordLoginTimelinePhase(`completeAuth:${phase}`, now - authPhaseMark);
          authPhaseMark = now;
        };
        const previousAuthUsername = clean(currentAuthUsername || "");
        const username = clean(payload.username || authUser.value);
        const authUserChanged = Boolean(
          previousAuthUsername &&
          username &&
          previousAuthUsername.toLowerCase() !== username.toLowerCase()
        );
        currentAuthUsername = username;
        currentAuthProfile = payload.profile && typeof payload.profile === "object" ? payload.profile : {};
        hologramCursorUserOverride = username;
        currentAuthIsAdmin = Boolean(payload.is_admin || payload.isAdmin);
        if (currentAuthIsAdmin) {
          try {
            pdfAdminActingUser = normalizePdfAdminActingUser(localStorage.getItem(PDF_ADMIN_ACTING_USER_KEY) || "");
          } catch (error) {
            pdfAdminActingUser = "";
          }
        } else {
          pdfAdminActingUser = "";
        }
        activeNpcActor = null;
        npcSwitchRoster = [];
        npcSwitchRosterLoadedAt = 0;
        authSessionInvalidating = false;
        loadHologramCursorSettings();
        loadQuestionMotionSettings();
        loadQuestionSideCardsSettings();
        loadQuestionAnimationSettings();
        applyHologramCursorPayload(payload.preferences || payload.prefs || {});
        applyQuestionMotionPayload(payload.preferences || payload.prefs || {});
        applyQuestionSideCardsPayload(payload.preferences || payload.prefs || {});
        applyQuestionAnimationPayload(payload.preferences || payload.prefs || {});
        applySpaceWVoicePayload(payload.preferences || payload.prefs || {});
        if (typeof applyVocabAudioPreferencePayload === "function") {
          applyVocabAudioPreferencePayload(payload.preferences || payload.prefs || {});
        }
        applyAiAgentGhostEnVoicePayload(payload.preferences || payload.prefs || {});
        applyLearnerChatVoicePayload(payload.preferences || payload.prefs || {});
        applyTaskNoticeProfilePayload(payload.preferences || payload.prefs || {});
        applyPdfCompactToolbarPayload(payload.preferences || payload.prefs || {});
        applyQuestionMotionSettings();
        applyQuestionSideCardsPreference();
        setAiAgentMode(getAiAgentMode(), false);
        recordAuthPhase("preferences");
        try {
          if (typeof syncVietnameseTypingSupportForUser === "function") {
            syncVietnameseTypingSupportForUser();
          }
          if (typeof syncSpeechInputModeControlsForUser === "function") {
            syncSpeechInputModeControlsForUser();
          }
        } catch (error) {
        }
        recordAuthPhase("input-controls");
        if (userNameNode) {
          userNameNode.textContent = username || "User";
        }
        if (userMenuName) {
          const fullName = clean(currentAuthProfile.full_name || currentAuthProfile.fullName || "");
          userMenuName.textContent = username ? (fullName ? `${fullName} | @${username}` : `Signed in: ${username}`) : "Sign in";
        }
        if (userAvatarStatus) {
          userAvatarStatus.textContent = authProfileAvatarPath(currentAuthProfile) ? "Avatar synced." : "No avatar yet.";
        }
        setUserAvatarNodes(currentAuthProfile, username);
        renderActiveUserIdentity();
        syncPdfAdminUserControls();
        recordAuthPhase("user-ui");
        try {
          if (typeof window.preloadPdfAiQuestionCharacter === "function") {
            window.preloadPdfAiQuestionCharacter();
          }
        } catch (error) {
        }
        recordAuthPhase("pdf-character-preload");
        if (authUserChanged) {
          try {
            if (typeof window.__ftResetLessonVaultProgressRuntimeCache === "function") {
              window.__ftResetLessonVaultProgressRuntimeCache();
            }
            serverBrowserPath = "";
            serverBrowserFocusedFilePath = "";
            serverTaskOwnerContext = "";
            currentTaskPayload = { task_owner: "", tasks: [], admin: false };
            clearServerBrowserListCache();
            clearLessonTaskPanelCache();
          } catch (error) {
          }
        }
        recordAuthPhase("user-change-cache");
        if (userButton) {
          userButton.classList.add("is-visible");
          userButton.setAttribute("aria-expanded", "false");
        }
        learnerChatMessages.length = 0;
        learnerChatPlayedAudioIds.clear();
        learnerChatLastId = 0;
        learnerChatUnread = 0;
        renderLearnerChatMessages();
        setLearnerChatVisible(true);
        void loadLearnerChatVoices();
        recordAuthPhase("learner-chat");
        startLearnerPaintPolling();
        startTaskNoticeImmediatePolling();
        if (typeof hasVocabRegistrySyncDirty === "function" ? hasVocabRegistrySyncDirty() : true) {
          scheduleVocabRegistrySync(1200);
        }
        recordAuthPhase("polling-schedulers");
        if (typeof seedProgressOutboxFromLocalStorage === "function") {
          seedProgressOutboxFromLocalStorage();
          scheduleProgressOutboxDrain(180);
        }
        recordAuthPhase("progress-outbox");
        if (typeof flushPdfDrawingPendingSaves === "function") {
          void flushPdfDrawingPendingSaves({ quiet: true });
        }
        recordAuthPhase("pdf-drawing-flush");
        stopAuthSessionMonitor();
        authSessionMonitorTimer = window.setInterval(() => {
          void fetchAuthJson("/auth/me").catch(() => {});
        }, 30000);
        if (userMenu) {
          userMenu.classList.remove("is-open");
        }
        recordAuthPhase("session-monitor");
        const hadLoginVaultRealBackdrop = Boolean(serverBrowser && serverBrowser.classList.contains("is-login-vault-backdrop"));
        try {
          clearStoredServerLastFileState(previousAuthUsername);
          clearStoredServerLastFileState(username);
          localStorage.setItem(AUTH_USER_KEY, username);
        } catch (error) {
        }
        if (payload.token || authToken) {
          persistAuthToken(payload.token || authToken);
        }
        if (typeof beginLessonVaultLoginRestore === "function") {
          beginLessonVaultLoginRestore(username, { startedAt: authResponseCompletedAt });
        }
        recordAuthPhase("auth-storage");
        // Updated 2026-07-28: the login tree already carries file word keys; never fetch the 4+ MB lesson index during login.
        const shouldOpenLessonVaultAfterAuth = Boolean(openLessonVaultAfterLogoutLogin)
          || Boolean(hadLoginVaultRealBackdrop)
          || Boolean(loadGate && !loadGate.classList.contains("is-hidden") && !reloadSessionRestorePending);
        // Updated 2026-07-31: start the authenticated snapshot warmup before the first Vault paint.
        const authVaultWarmupPromise = typeof startLoginVaultWarmup === "function"
          ? Promise.resolve(startLoginVaultWarmup("submit")).catch(() => null)
          : Promise.resolve(null);
        openLessonVaultAfterLogoutLogin = false;
        const closeAuthGateAfterSuccess = () => {
          if (authGate) {
            authGate.classList.add("is-hidden");
          }
          if (typeof setLoginVaultPreviewVisible === "function") {
            setLoginVaultPreviewVisible(false);
          }
          stopAuthFocusMotion();
          if (authPass) {
            authPass.value = "";
          }
          if (authConfirm) {
            authConfirm.value = "";
          }
          stopAuthAnnouncements();
          setAuthStatus("");
          if (authSubmit) {
            authSubmit.disabled = false;
          }
        };
        if (shouldOpenLessonVaultAfterAuth) {
          if (typeof clearLoginVaultRealBackdrop === "function") {
            clearLoginVaultRealBackdrop();
          }
          if (authSubmit) {
            authSubmit.disabled = true;
          }
          closeAuthGateAfterSuccess();
          // Added 2026-07-28: do not hold the login promise on the first Lesson Vault paint.
          const openVaultAfterAuth = async () => {
            try {
              if (typeof waitForLoginVaultWarmup === "function") {
                await waitForLoginVaultWarmup(username, 900);
              }
              const openedPayload = await openServerBrowserAfterAuth({
                revealAfterLoad: false,
                silent: false,
                throwOnError: true,
                skipTaskBoardHydrate: true,
                skipBackgroundVerify: true,
                skipChildPrefetch: true,
              });
              if (typeof schedulePostAuthLessonVaultHydration === "function") {
                schedulePostAuthLessonVaultHydration(openedPayload || null, username, authVaultWarmupPromise);
              }
            } catch (error) {
              await Promise.resolve(openServerBrowserAfterAuth()).catch(() => {});
            }
          };
          void openVaultAfterAuth();
          recordAuthPhase("open-vault-scheduled");
        } else if (typeof clearLoginVaultRealBackdrop === "function") {
          clearLoginVaultRealBackdrop();
          closeAuthGateAfterSuccess();
          recordAuthPhase("close-auth-only");
        }
        if (typeof window !== "undefined" && typeof window.__ftRecordLoginTimelinePhase === "function") {
          window.__ftRecordLoginTimelinePhase("completeAuth:total", authTimelineNow() - authPhaseStart);
        }
      };

      const clearStoredAuthToken = () => {
        authToken = "";
        forgetStoredAuthToken();
      };

      const setLoginVaultPreviewVisible = (visible = false, options = {}) => {
        const enabled = Boolean(visible);
        const showStaticPreview = Boolean(enabled && !options.realOnly);
        if (loginVaultPreview) {
          loginVaultPreview.classList.toggle("is-visible", showStaticPreview);
        }
        if (authGate) {
          authGate.classList.toggle("is-login-vault-preview", enabled);
        }
      };

      const clearLoginVaultRealBackdrop = (options = {}) => {
        loginVaultBackdropSerial += 1;
        loginVaultBackdropBusy = false;
        if (serverBrowser) {
          serverBrowser.classList.remove("is-login-vault-backdrop");
          if (options.hideBrowser) {
            serverBrowser.hidden = true;
            syncServerWorkspaceOpenState();
          }
        }
      };

      // Added 2026-07-09: keeps floating lesson/PDF panels from staying interactive above the login gate after session loss.
      const sealFloatingPanelsForLoginGate = () => {
        document.documentElement.classList.remove("ft-mobile-tools-open");
        if (mobileToolsToggle) {
          mobileToolsToggle.classList.remove("is-active");
          mobileToolsToggle.setAttribute("aria-expanded", "false");
        }
        document.querySelectorAll(".ft-server-recent-popover,.ft-pdf-pin-popover,.ft-pdf-local-image-popover").forEach((node) => {
          node.classList.remove("is-visible");
          node.setAttribute("aria-hidden", "true");
        });
      };

      const createLoginVaultBackdropPayload = () => {
        const today = new Date().toISOString();
        const vocabPath = "hung/Immediate Mission/Unit 1 Missing Words.Space_V";
        const paragraphPath = "hung/Bai doc/Dich cau va phan tich ngu phap/How tennis rackets have changed.Space_P";
        const questionPath = "hung/Ngu phap/Present Simple Practice.Space_Q";
        const pdfPath = "common/PDF/Class 11 Reading Book.pdf";
        const fileStudy = (percent, text, extra = {}) => ({
          mine: 1,
          total: 1,
          nodes: Number(extra.nodes || 0) || 0,
          mine_last: today,
          title: clean(extra.title || ""),
          progress: { percent, text },
          progress_percent: percent,
          progress_text: text,
          time_seconds: Number(extra.time_seconds || 0) || 0,
          admin_view: true,
          admin_progress: {
            percent: Math.min(100, Math.max(0, Number(percent || 0) + 8)),
            text: clean(extra.adminText || text),
          },
        });
        const tasks = [
          {
            id: "login-preview-task-v",
            path: vocabPath,
            title: "Unit 1 Missing Words",
            name: "Unit 1 Missing Words.Space_V",
            severity: "critical",
            completed: false,
            creator_role: "admin",
            added_by: "admin",
            assigned_at: today,
            user_count: 1,
            study: fileStudy(62, "16/25 words", { title: "Unit 1 Missing Words", time_seconds: 1320 }),
          },
          {
            id: "login-preview-task-p",
            path: paragraphPath,
            title: "How tennis rackets have changed",
            name: "How tennis rackets have changed.Space_P",
            severity: "high",
            completed: false,
            creator_role: "admin",
            added_by: "admin",
            assigned_at: today,
            user_count: 2,
            study: fileStudy(38, "5/13 sentences", { title: "How tennis rackets have changed", nodes: 13, time_seconds: 980 }),
          },
          {
            id: "login-preview-task-q",
            path: questionPath,
            title: "Present Simple Practice",
            name: "Present Simple Practice.Space_Q",
            severity: "normal",
            completed: true,
            creator_role: "admin",
            added_by: "admin",
            assigned_at: today,
            completed_at: today,
            user_count: 1,
            study: fileStudy(100, "24/24 questions", { title: "Present Simple Practice", nodes: 24, time_seconds: 740 }),
          },
        ];
        return {
          admin: true,
          username: "hung",
          task_owner: "hung",
          login_preview: true,
          path: "hung",
          parent: "",
          learning_stats: {
            vocabulary_words: 572,
            space_v_files: 18,
            space_w_files: 7,
            space_q_files: 9,
            space_p_files: 4,
          },
          task_notices: [],
          tasks,
          entries: [
            { type: "folder", owner: "personal", name: "Immediate Mission", path: "hung/Immediate Mission", file_count: 7, word_count: 175, space_v_file_count: 7 },
            { type: "folder", owner: "shared", name: "Common", path: "common", file_count: 42, word_count: 2961, space_v_file_count: 28, virtual_common: true, task_owner: "hung" },
            { type: "file", name: "Unit 1 Missing Words.Space_V", path: vocabPath, extension: ".space_v", size: 42000, study: tasks[0].study, task: tasks[0] },
            { type: "file", name: "How tennis rackets have changed.Space_P", path: paragraphPath, extension: ".space_p", size: 86000, study: tasks[1].study, task: tasks[1] },
            { type: "file", name: "Present Simple Practice.Space_Q", path: questionPath, extension: ".space_q", size: 54000, study: tasks[2].study, task: tasks[2] },
            { type: "file", name: "Class 11 Reading Book.pdf", path: pdfPath, extension: ".pdf", size: 3200000, study: fileStudy(18, "Page 11/62", { title: "Class 11 Reading Book", time_seconds: 420 }) },
          ],
        };
      };

      const renderLoginVaultDemoBackdrop = () => {
        // 2026-07-27: restore the lightweight Hưng Lesson Vault backdrop from static JS data only.
        if (!serverBrowser || typeof renderServerDataList !== "function") {
          setLoginVaultPreviewVisible(true);
          return false;
        }
        const serial = loginVaultBackdropSerial + 1;
        loginVaultBackdropSerial = serial;
        loginVaultBackdropBusy = false;
        try {
          renderServerDataList(createLoginVaultBackdropPayload());
          serverBrowser.hidden = false;
          serverBrowser.classList.add("is-login-vault-backdrop");
          setServerBrowserPanel("vault");
          syncServerWorkspaceOpenState();
          setLoginVaultPreviewVisible(true, { realOnly: true });
          return true;
        } catch (error) {
          if (loginVaultBackdropSerial === serial) {
            clearLoginVaultRealBackdrop({ hideBrowser: true });
          }
          setLoginVaultPreviewVisible(true);
          return false;
        }
      };

      const loadLoginVaultRealBackdrop = () => {
        loginVaultBackdropBusy = false;
        return renderLoginVaultDemoBackdrop();
      };

      const showLoginGate = (message = "Sign in to continue.", options = {}) => {
        const backdropUser = clean(options.backdropUser || currentAuthUsername || (() => {
          try {
            return localStorage.getItem(AUTH_USER_KEY) || "";
          } catch (error) {
            return "";
          }
        })() || (authUser && authUser.value) || "");
        updateFutureAppRoute("login", { replace: true });
        stopAuthSessionMonitor();
        clearStoredAuthToken();
        resetActiveLearningModesForAuth();
        if (authUser && backdropUser) {
          authUser.value = backdropUser;
        }
        currentAuthUsername = "";
        currentAuthProfile = {};
        hologramCursorUserOverride = "";
        currentAuthIsAdmin = false;
        activeNpcActor = null;
        npcSwitchRoster = [];
        npcSwitchRosterLoadedAt = 0;
        resetPdfAdminActingUserState({ clearUsers: true });
        sealFloatingPanelsForLoginGate();
        setUserAvatarNodes({}, "");
        syncPdfAdminUserControls();
        if (userButton) {
          userButton.classList.remove("is-visible");
          userButton.setAttribute("aria-expanded", "false");
        }
        if (userMenu) {
          userMenu.classList.remove("is-open");
        }
        if (authGate) {
          authGate.classList.remove("is-hidden");
        }
        stopAuthFocusMotion();
        startAuthAnnouncements();
        window.requestAnimationFrame(positionAuthConnectors);
        window.setTimeout(positionAuthConnectors, 260);
        setAuthMode("login");
        setAuthStatus(message);
        if (!loadLoginVaultRealBackdrop()) {
          setLoginVaultPreviewVisible(true);
        }
      };

      const revealLoginGateForSessionCheck = (savedUser = "", message = "Checking your login session...") => {
        stopAuthSessionMonitor();
        stopLearnerChatPolling();
        stopLearnerStreamPolling();
        stopLearnerScreenPolling();
        stopLearnerPaintPolling();
        setLearnerChatVisible(false);
        currentAuthUsername = "";
        currentAuthProfile = {};
        hologramCursorUserOverride = "";
        currentAuthIsAdmin = false;
        activeNpcActor = null;
        npcSwitchRoster = [];
        npcSwitchRosterLoadedAt = 0;
        resetPdfAdminActingUserState({ clearUsers: true });
        sealFloatingPanelsForLoginGate();
        setUserAvatarNodes({}, "");
        syncPdfAdminUserControls();
        if (userButton) {
          userButton.classList.remove("is-visible");
          userButton.setAttribute("aria-expanded", "false");
        }
        if (userMenu) {
          userMenu.classList.remove("is-open");
        }
        if (authGate) {
          authGate.classList.remove("is-hidden");
        }
        setLoginVaultPreviewVisible(true);
        if (authUser && savedUser) {
          authUser.value = savedUser;
        }
        if (authSubmit) {
          authSubmit.disabled = false;
        }
        stopAuthFocusMotion();
        startAuthAnnouncements();
        window.requestAnimationFrame(positionAuthConnectors);
        window.setTimeout(positionAuthConnectors, 260);
        setAuthMode("login");
        setAuthStatus(message);
      };

      const authTokenStillCurrent = (token = "") => {
        const expected = clean(token);
        if (!expected) {
          return false;
        }
        return clean(authToken || getStoredAuthToken()) === expected;
      };

      const logoutAuth = () => {
        const logoutBackdropToken = clean(authToken || getStoredAuthToken());
        const logoutBackdropUser = clean(currentAuthUsername || (() => {
          try {
            return localStorage.getItem(AUTH_USER_KEY) || "";
          } catch (error) {
            return "";
          }
        })() || (authUser && authUser.value) || "");
        if (typeof cancelLessonVaultLoginRestore === "function") {
          cancelLessonVaultLoginRestore("logout", { userInteracted: false });
        }
        try {
          forgetStoredAuthToken();
          sessionStorage.removeItem(RELOAD_SESSION_KEY);
        } catch (error) {
        }
        authToken = "";
        authPass.value = "";
        authConfirm.value = "";
        pendingSpaceWAfterVocabulary = null;
        currentVocabularyMission = null;
        vocabPreflightState = null;
        vocabPreflightBuildToken += 1;
        spaceWVocabBuildGuardPath = "";
        spaceWVocabSkipPaths = new Set();
        spaceWVocabClearedPaths = new Set();
        stopTaskNoticeImmediatePolling();
        resetSpaceWCache();
        resetParagraphMode();
        resetParagraphProgressCache();
        try {
          if (typeof window.__ftResetLessonVaultProgressRuntimeCache === "function") {
            window.__ftResetLessonVaultProgressRuntimeCache();
          }
        } catch (error) {
        }
        try {
          serverBrowserPath = "";
          serverBrowserFocusedFilePath = "";
          serverTaskOwnerContext = "";
          currentTaskPayload = { task_owner: "", tasks: [], admin: false };
          clearServerBrowserListCache();
          clearLessonTaskPanelCache();
        } catch (error) {
        }
        openLessonVaultAfterLogoutLogin = true;
        try {
          if (typeof resetPdfMode === "function") {
            resetPdfMode();
          }
        } catch (error) {
        }
        updateFutureAppRoute("login", { replace: true });
        hideVocabPreflightGate();
        showLoginGate("You have been signed out. Sign in again to continue learning.", {
          backdropToken: logoutBackdropToken,
          backdropUser: logoutBackdropUser,
        });
        showMobileLogoutFullscreenGate();
      };

      const readReloadSessionState = (consume = false) => {
        try {
          const raw = window.sessionStorage && window.sessionStorage.getItem(RELOAD_SESSION_KEY);
          if (!raw) {
            return null;
          }
          const state = JSON.parse(raw);
          if (!state || typeof state !== "object" || Number(state.expiresAt || 0) < Date.now()) {
            window.sessionStorage.removeItem(RELOAD_SESSION_KEY);
            return null;
          }
          if (consume) {
            window.sessionStorage.removeItem(RELOAD_SESSION_KEY);
          }
          return state;
        } catch (error) {
          try {
            window.sessionStorage.removeItem(RELOAD_SESSION_KEY);
          } catch (_error) {
          }
          return null;
        }
      };

      const writeReloadSessionState = () => {
        if (!authToken) {
          return false;
        }
        const sourcePath = clean(currentLessonSource && currentLessonSource.path || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
        const hasActiveLesson = Boolean(sourcePath && (vocabModeActive || questionModeActive || paragraphModeActive || lessonNodes.length));
        const routeState = futureRouteStateFromLocation();
        const routeIsLessonVault = !hasActiveLesson && normalizeFutureAppRoute(routeState.route || "") === "lesson_vault";
        const storedPath = typeof getStoredServerPath === "function" ? getStoredServerPath() : "";
        const selectedFile = cleanFutureRoutePathValue(
          sourcePath ||
          routeState.file ||
          serverBrowserFocusedFilePath ||
          (typeof getStoredServerFile === "function" ? getStoredServerFile() : "")
        );
        const browserPath = cleanFutureRoutePathValue(
          (sourcePath ? futureRouteParentForPath(sourcePath) : "") ||
          routeState.tree ||
          serverBrowserPath ||
          storedPath ||
          (selectedFile ? futureRouteParentForPath(selectedFile) : "")
        );
        if (!hasActiveLesson && routeState.route !== "lesson_vault" && !browserPath && !selectedFile) {
          return false;
        }
        const mode = hasActiveLesson
          ? (vocabModeActive ? "space_v" : (questionModeActive ? "space_q" : (paragraphModeActive ? "space_p" : "space_w")))
          : (routeIsLessonVault ? "lesson_vault" : (routeState.process || futureRouteSpaceForFilePath(selectedFile) || routeState.route || "lesson_vault"));
        try {
          const now = Date.now();
          window.sessionStorage.setItem(RELOAD_SESSION_KEY, JSON.stringify({
            version: 1,
            savedAt: now,
            expiresAt: now + RELOAD_SESSION_TTL_MS,
            token: authToken,
            username: currentAuthUsername,
            mode,
            routeState: {
              route: routeState.route || mode,
              tree: browserPath,
              file: routeIsLessonVault ? "" : selectedFile,
              process: routeIsLessonVault ? "" : mode,
            },
            source: hasActiveLesson ? { ...(currentLessonSource || {}) } : {},
            path: hasActiveLesson ? sourcePath : "",
            selectedFile,
            browserPath,
          }));
          return true;
        } catch (error) {
          return false;
        }
      };

      const restoreAuthSession = async () => {
        const warmReloadSessionCaches = () => {
          if (typeof startLoginVaultWarmup !== "function") {
            return Promise.resolve(null);
          }
          try {
            // A frontend bump clears client RAM, so rebuild the same compact caches as a password login.
            return Promise.resolve(startLoginVaultWarmup("submit")).catch(() => null);
          } catch (error) {
            return Promise.resolve(null);
          }
        };
        const initialRouteState = futureRouteStateFromLocation();
        const reloadState = readReloadSessionState(false);
        if (initialRouteState.route === "login" && !(reloadState && reloadState.token)) {
          let savedUser = "";
          let savedToken = "";
          try {
            savedToken = getStoredAuthToken();
            savedUser = localStorage.getItem(AUTH_USER_KEY) || "";
            sessionStorage.removeItem(RELOAD_SESSION_KEY);
          } catch (error) {
          }
          reloadSessionRestorePending = false;
          clearStoredAuthToken();
          authToken = "";
          if (authUser && savedUser) {
            authUser.value = savedUser;
          }
          showLoginGate(savedUser ? "Enter your password to sign in again." : "Sign in to continue.", {
            backdropToken: savedToken,
            backdropUser: savedUser,
          });
          return;
        }
        if (reloadState && reloadState.token) {
          reloadSessionRestorePending = true;
          const restoreToken = clean(reloadState.token);
          const restoreGateTimer = window.setTimeout(() => {
            if (authTokenStillCurrent(restoreToken)) {
              revealLoginGateForSessionCheck(reloadState.username || "", "Dang khoi phuc phien dang nhap...");
            }
          }, 520);
          persistAuthToken(restoreToken);
          try {
            const result = await fetchAuthJson("/auth/me");
            window.clearTimeout(restoreGateTimer);
            if (!authTokenStillCurrent(restoreToken)) {
              reloadSessionRestorePending = false;
              return;
            }
            const payload = result.payload || {};
            if (authUser) {
              authUser.value = payload.username || reloadState.username || "";
            }
              completeAuth({
                ...payload,
                username: payload.username || reloadState.username || "",
              });
              const cacheWarmup = warmReloadSessionCaches();
              window.setTimeout(() => {
                const hasLessonPath = clean(reloadState.path || (reloadState.source && reloadState.source.path) || "");
                const restoreTask = cacheWarmup.then(() => (
                  hasLessonPath
                    ? restoreLessonAfterReloadSession(reloadState)
                    : restoreBrowserAfterReloadSession(reloadState)
                ));
                void restoreTask.finally(() => {
                  reloadSessionRestorePending = false;
                });
            }, 80);
            return;
          } catch (error) {
            window.clearTimeout(restoreGateTimer);
            reloadSessionRestorePending = false;
            if (!authTokenStillCurrent(restoreToken)) {
              return;
            }
            clearStoredAuthToken();
            try {
              sessionStorage.removeItem(RELOAD_SESSION_KEY);
            } catch (_error) {
            }
          }
        }
        let savedUser = "";
        let savedToken = "";
        try {
          savedToken = getStoredAuthToken();
          savedUser = localStorage.getItem(AUTH_USER_KEY) || "";
          if (savedUser && authUser) {
            authUser.value = savedUser;
          }
        } catch (error) {
          authToken = "";
        }
        if (savedToken) {
          reloadSessionRestorePending = true;
          const restoreToken = clean(savedToken);
          const restoreGateTimer = window.setTimeout(() => {
            if (authTokenStillCurrent(restoreToken)) {
              revealLoginGateForSessionCheck(savedUser || "", "Dang kiem tra phien dang nhap...");
            }
          }, 520);
          persistAuthToken(restoreToken);
          try {
            const result = await fetchAuthJson("/auth/me");
            window.clearTimeout(restoreGateTimer);
            if (!authTokenStillCurrent(restoreToken)) {
              reloadSessionRestorePending = false;
              return;
            }
            const payload = result.payload || {};
            if (authUser) {
              authUser.value = payload.username || savedUser || "";
            }
              void completeAuth({
                ...payload,
                username: payload.username || savedUser || "",
              });
              const cacheWarmup = warmReloadSessionCaches();
              window.setTimeout(() => {
              const routeState = futureRouteStateFromLocation();
              const routeHasTarget = Boolean(routeState.file || routeState.tree || (routeState.route && routeState.route !== "login"));
              const restoreState = {
                version: 1,
                token: savedToken,
                username: payload.username || savedUser || "",
                mode: routeState.process || routeState.route || futureRouteSpaceForFilePath(routeState.file) || "lesson_vault",
                routeState,
                selectedFile: routeState.file || "",
                browserPath: routeState.tree || (routeState.file ? futureRouteParentForPath(routeState.file) : ""),
                source: routeState.file ? {
                  source: "server",
                  path: routeState.file,
                  name: routeState.file.split("/").pop() || routeState.file,
                } : {},
                path: routeState.file && routeState.route && routeState.route.startsWith("space_") ? routeState.file : "",
                directRouteRestore: Boolean(routeState.file && routeState.route && routeState.route.startsWith("space_")),
                allowDuringVocabBuild: Boolean(routeState.file && routeState.route && routeState.route.startsWith("space_")),
              };
                const restoreTask = cacheWarmup.then(() => (
                  routeHasTarget
                    ? (restoreState.path ? restoreLessonAfterReloadSession(restoreState) : restoreBrowserAfterReloadSession(restoreState))
                    : Promise.resolve(openServerBrowserAfterAuth())
                ));
              void Promise.resolve(restoreTask).finally(() => {
                reloadSessionRestorePending = false;
              });
            }, 80);
            return;
          } catch (error) {
            window.clearTimeout(restoreGateTimer);
            reloadSessionRestorePending = false;
            if (!authTokenStillCurrent(restoreToken)) {
              return;
            }
            clearStoredAuthToken();
          }
        }
        authToken = "";
        showLoginGate(savedUser ? "Enter your password to sign in again." : "Sign in to continue.");
      };

      const handleAuthSubmit = async () => {
        const username = clean(authUser.value);
        const password = authPass.value || "";
        setAuthStatus("Sending to server...");
        authSubmit.disabled = true;
        try {
          if (!username) {
            throw new Error("Vui lòng nhập tên tài khoản.");
          }
          if (authMode === "reset") {
            if (authResetApproved) {
              if (!password) {
                throw new Error("Vui long nhap mat khau moi.");
              }
              if (password !== (authConfirm.value || "")) {
                throw new Error("The confirmation password does not match.");
              }
              await fetchAuthJson("/auth/password-reset/confirm", {
                method: "POST",
                body: JSON.stringify({ username, password, new_password: password }),
              });
              authResetApproved = false;
              authPass.value = "";
              authConfirm.value = "";
              if (authResetCode) authResetCode.value = "";
              setAuthMode("login");
              setAuthStatus("Password changed. Sign in with your new password.", "ok");
              return;
            }
            await fetchAuthJson("/auth/password-reset/request", {
              method: "POST",
              body: JSON.stringify({ username }),
            });
            authPass.value = "";
            authConfirm.value = "";
            if (authResetCode) authResetCode.value = "";
            setAuthStatus("Request sent. After admin approval, check approval again to set a new password.", "ok");
            return;
          }
          if (!password) {
            throw new Error("Vui lòng nhập mật khẩu.");
          }
          if (authMode === "register") {
            if (password !== (authConfirm.value || "")) {
              throw new Error("The confirmation password does not match.");
            }
            const payload = {
              username,
              password,
              ...authProfilePayload(),
            };
            await fetchAuthJson("/auth/register", {
              method: "POST",
              body: JSON.stringify(payload),
            });
            setAuthStatus("Registration request sent. Wait for server approval, then sign in.", "ok");
            authPass.value = "";
            authConfirm.value = "";
            setAuthMode("login");
            return;
          }
          if (authMode === "profile") {
            const result = await fetchAuthJson("/auth/profile", {
              method: "POST",
              body: JSON.stringify(authProfilePayload()),
            });
            await completeAuth(result.payload || {});
            return;
          }
          const result = await fetchAuthJson("/auth/login", {
            method: "POST",
            body: JSON.stringify({ username, password }),
          });
          const payload = result.payload || {};
          authToken = "";
          persistAuthToken(payload.token || "");
          authUser.value = payload.username || username;
          authPass.value = "";
          authConfirm.value = "";
          if (payload.needs_profile) {
            setAuthMode("profile", payload.profile || {});
            setAuthStatus("Vui long cap nhat ho ten, gioi tinh va ngay sinh.", "error");
            return;
          }
          await completeAuth(payload);
          if (typeof startLoginVaultWarmup === "function") {
            void startLoginVaultWarmup("submit");
          }
        } catch (error) {
          setAuthStatus(error && error.message ? error.message : "Khong dang nhap duoc.", "error");
        } finally {
          authSubmit.disabled = false;
        }
      };

      const normalize = (value) =>
        clean(value)
          .toLowerCase()
          .replace(/[’']/g, "")
          .replace(/[^a-z0-9 ]+/g, "")
          .replace(/\b(a|an|the)\b/g, "")
          .replace(/\s+/g, " ")
          .trim();

      const question = clean(params.get("vi")) || defaults.vi;
      const answer = clean(params.get("en")) || defaults.en;
      const ipa = clean(params.get("ipa")) || defaults.ipa;
      let voiceHint = clean(params.get("voice")) || SPACE_W_DEFAULT_VOICE;
      let wrongAttempts = 0;
      let speechVoices = [];
      let activeAudio = null;
      let highlightFrame = 0;
      let highlightTimer = 0;
      let revealTimer = 0;
      let connectorTimer = 0;
      let connectorTargetPanel = null;
      let hintTypingTimer = 0;
      let hintTypingToken = 0;
      let aboutTypingTimer = 0;
      let aboutTypingToken = 0;
      let aboutItems = [];
      let aboutIndex = 0;
      let aboutUnlockedForCurrentNode = false;
      let spaceWTrainModeLocked = false;
      let spaceWTrainModeBuffer = [];
      let spaceWTrainModeOriginalCount = 0;
      let spaceWTrainModeRootCount = 0;
      let spaceWTrainModeExpanded = false;
      let spaceWTrainModeBatch = 0;
      let speakRecorder = null;
      let speakStream = null;
      let speakChunks = [];
      let speakBusy = false;
      let speakRecordedBlob = null;
      let speakRecordedUrl = "";
      let speakReplayAudio = null;
      let spaceWScoringTokenAudio = null;
      let spaceWScoringTokenAudioWarmKey = "";
      let speakWaveFrame = 0;
      let speakWaveMode = "idle";
      let speakWaveStartedAt = 0;
      let speakWaveAudioContext = null;
      let speakWaveAnalyser = null;
      let speakWaveSource = null;
      let speakWaveFrequencyData = null;
      let speakWaveStaticRows = [];
      let speakReplayUnlockContext = null;
      let speakReplayBufferSource = null;
      const SPACE_W_SPEAK_AI_CHECK_KEY = "future_space_w_ai_check_voice";
      // Added 2026-07-30: Record defaults to local browser scoring so a settings request can never block the mic.
      let speakAiCheckVoice = false;
      let speakAiCheckVoiceServerManaged = false;
      let speakAiCheckVoiceServerAllowsWhisper = true;
      let speakAiCheckVoiceFallbackActive = false;
      let speakRecognition = null;
      let speakRecognitionActive = false;
      let speakRecognitionManualStop = false;
      let speakRecognitionTranscript = "";
      let speakRecognitionChunkText = "";
      let speakRecognitionLastError = "";
      let speakBrowserRecordingStartedAt = 0;
      let speakBrowserTokenTimeline = [];
      let speakReplayHighlightFrame = 0;
      let speakAutoReplayTimer = 0;
      let speakUserTokenClipAudio = null;
      let lessonNodes = [];
      let pendingLessonNodes = [];
      let pendingLessonEffects = {};
      let pendingVocabularyPayload = null;
      let pendingQuestionPayload = null;
      let pendingParagraphPayload = null;
      let currentLessonSource = { source: "", path: "", name: "", title: "", study: null };
      let lessonStudyTimeTimer = 0;
      let lessonStudyTimeBusy = false;
      let lessonStudyTimePath = "";
      let lessonStudyTimeSessionId = "";
      let lessonStudyTimeSequence = 0;
      let lessonStudyTimeOfflineLease = "";
      let currentSpaceWCache = { identity: "", progressKey: "", voiceKey: "", voiceValue: "", voiceLabel: "", voiceApplied: false, savedProgress: null };
      let spaceWVoicePreference = { value: "", label: "", updatedAt: "" };
      let spaceWNodeProgress = {};
      let spaceWProgressSaveTimer = 0;
      let spaceWServerProgressSaveTimer = 0;
      let pendingSpaceWServerProgressRecord = null;
      let spaceWServerProgressSyncBusy = false;
      let spaceWLoadDecisionToken = 0;
      let spaceWAudioDbPromise = null;
      let spaceWAudioPersistentWrites = 0;
      let spaceWAudioPreloadToken = 0;
      let lessonAudioPrepareToken = 0;
      let lessonAudioBackgroundToken = 0;
      let lessonAudioPrepareBusy = false;
      let lessonAudioPrepareMode = "";
      const LESSON_AUDIO_BACKGROUND_START_DELAY_MS = 1400;
      const LESSON_AUDIO_BACKGROUND_NODE_LIMIT = 2;
      const LESSON_AUDIO_BACKGROUND_TASK_LIMIT = 4;
      const pendingSpaceWAudioCacheTasks = new Map();
      const GENERIC_AUDIO_CACHE_PREFIX = "generic-audio:";
      const GENERIC_MEDIA_AUDIO_CACHE_PREFIX = "media-audio:v1:";
      let pendingSpaceWAfterVocabulary = null;
      let currentVocabularyMission = null;
      let vocabPreflightState = null;
      let vocabPreflightBusy = false;
      let vocabPreflightBuildToken = 0;
      let spaceWVocabBuildGuardPath = "";
      let spaceWVocabSkipPaths = new Set();
      let spaceWVocabClearedPaths = new Set();
      let lessonCompletionSent = false;
      let spaceWActiveRunId = "";
      let completionSyncBusy = false;
      let currentNodeIndex = 0;
      let currentNode = null;
      let vocabModeActive = false;
      let paragraphModeActive = false;
      let vocabItems = [];
      let vocabQueue = [];
      let vocabBatch = [];
      let vocabRoundQueue = [];
      let vocabCurrentIndex = -1;
      let vocabCurrentHadError = false;
      let vocabLearnedKeys = new Set();
      let vocabRegistryWords = [];
      let vocabRegistryKeys = new Set();
      let vocabRegistryPeriodKeys = { day: new Set(), week: new Set(), month: new Set() };
      let vocabRegistryTotal = 0;
      let vocabRegistryLoaded = false;
      let vocabRegistryLoading = false;
      let vocabRegistryFilterText = "";
      let vocabRegistryError = "";
      let vocabAttemptCounts = new Map();
      let vocabStudyIndexes = [];
      let vocabStudyKeys = new Set();
      let vocabKnownAtStartKeys = new Set();
      let vocabBlueCrystalReadyKeys = new Set();
      let vocabPhase = "probe";
      let vocabDrillIndex = 0;
      let vocabDrillCorrectCount = 0;
      let vocabDrillFailCount = 0;
      let vocabShuffleOriginal = [];
      let vocabShuffleRound = 0;
      let vocabShuffleQueue = [];
      let vocabShuffleCorrectCount = 0;
      let vocabShuffleFailCount = 0;
      let vocabAnswerSubmitLockUntil = 0;
      let vocabCompletionFinalizing = false;
      let vocabReviewRunActive = false;
      let vocabActiveRunId = "";
      let vocabInputResetToken = 0;
      let vocabInputResetUntil = 0;
      let vocabQuestionToken = 0;
      let vocabHintTimers = [];
      let vocabHintToken = 0;
      let vocabIdleHintTimer = 0;
      let vocabIdleHintToken = 0;
      let vocabActiveHintKind = "";
      let vocabActiveHintIndex = -1;
      let vocabActiveHintPhase = "";
      let vocabAutoRevealLock = false;
      let vocabAnswerBusy = false;
      let vocabAnswerAudioToken = 0;
      let vocabAudioCacheToken = 0;
      let vocabMeaningAudioToken = 0;
      let vocabMeaningAudioRef = null;
      let vocabMeaningAudioDone = null;
      let vocabImageLoadToken = 0;
      const vocabImageFetchInflight = new Set();
      const vocabImageResultCache = new Map();
      const vocabImageRetryCounts = new Map();
      const vocabImageBytePrefetches = new Map();
      const VOCAB_IMAGE_DB_NAME = "future_vocab_image_cache";
      const VOCAB_IMAGE_DB_STORE = "images";
      const VOCAB_IMAGE_DB_VERSION = 3;
      const VOCAB_IMAGE_MEDIA_KEY_VERSION = 2;
      const VOCAB_IMAGE_CACHE_MAX_ENTRIES = 192;
      const VOCAB_IMAGE_CACHE_MAX_BYTES = 64 * 1024 * 1024;
      const OFFLINE_STORAGE_ESTIMATE_REFRESH_MS = 60 * 1000;
      let vocabImageDbPromise = null;
      let vocabImagePersistentWrites = 0;
      const vocabImageBlobUrls = new Map();
      let offlineStoragePersistencePromise = null;
      let offlineStorageLastCheckedAt = 0;
      let offlineStoragePressure = "unknown";
      let vocabImagePrefetchTimer = 0;
      let vocabModePopupTimer = 0;
      let vocabModeTransitioning = false;
      let currentVocabProgressCache = {
        identity: "",
        progressKey: "",
        savedProgress: null,
        serverPayload: null,
        serverEtag: "",
        serverProgressPromise: null,
        serverProgressResult: null,
        serverProgressSettled: false,
      };
      let vocabProgressSaveTimer = 0;
      let vocabServerProgressSaveTimer = 0;
      let pendingVocabServerProgressRecord = null;
      let vocabServerProgressInFlight = 0;
      let vocabServerProgressLastErrorAt = 0;
      let vocabProgressLastSemanticSignature = "";
      let vocabRegistrySyncTimer = 0;
      let vocabRegistrySyncBusy = false;
      let vocabLoadDecisionToken = 0;
      let edgeCatalogRequested = false;
      let currentAccent = "uk";
      let vocabVoiceKey = "sot:en-GB";
      let vocabPulseTimer = 0;
      let lastVocabPulseKey = "";
      const lessonProgressOverrides = new Map();
      let questionPayload = null;
      let currentQuestionProgressCache = { identity: "", progressKey: "", savedProgress: null };
      let questionProgressSaveTimer = 0;
      let questionProgressLastSemanticSignature = "";
      let questionServerProgressSaveTimer = 0;
      let pendingQuestionServerProgressRecord = null;
      let questionServerProgressSyncBusy = false;
      let questionLoadDecisionToken = 0;
      let pendingQuestionResumeState = null;
      let questionReviewRunActive = false;
      let questionActiveRunId = "";
      let paragraphReviewRunActive = false;
      let paragraphActiveRunId = "";
      let currentParagraphProgressCache = { identity: "", progressKey: "", savedProgress: null, serverPayload: null, serverEtag: "" };
      let paragraphProgressSaveTimer = 0;
      let paragraphServerProgressSaveTimer = 0;
      let pendingParagraphServerProgressRecord = null;
      let paragraphServerProgressSyncBusy = false;
      let paragraphProgressLastSemanticSignature = "";
      let paragraphLoadDecisionToken = 0;
      let questionNodes = [];
      let questionQueue = [];
      let questionNodePointer = 0;
      let questionCurrentNode = null;
      let questionCurrentQuestions = [];
      let questionCurrentQuestionOrder = [];
      let questionQuestionIndex = 0;
      let questionWrongAttempts = 0;
      const questionFirstTryAnsweredKeys = new Set();
      const questionFirstTryCorrectKeys = new Set();
      let questionRunAttemptSeed = "";
      let questionAttemptSerial = 0;
      let questionCurrentAttemptSignature = "";
      let questionCurrentAttemptKey = "";
      let questionTypingTimer = 0;
      let questionRootOpenTypingTimer = 0;
      let questionAdvanceTimer = 0;
      let questionTypingToken = 0;
      let questionRevealTimer = 0;
      let questionRevealToken = 0;
      let questionCameraPanTimer = 0;
      let questionCameraPanToken = 0;
      let questionManualFocusTimer = 0;
      let questionFocusPointerState = null;
      let questionManualFocusTarget = null;
      let questionRootHighlightTimer = 0;
      let questionRootHighlightToken = 0;
      let questionRootHighlightLastSignature = "";
      let questionRootHighlightLastNode = null;
      let questionHighlightCameraFocusToken = 0;
      let questionCardRevealToken = 0;
      let questionCardRevealSkin = 0;
      let questionInputFlareTimer = 0;
      let questionAnswerInputLastValue = "";
      let questionCardActiveAudio = null;
      let questionNextTransitionActive = false;
      let questionSelectCompletionTimer = 0;
      let questionSelectCompletionToken = 0;
      let questionSelectAnswerRevealTimer = 0;
      let questionSelectAnswerRevealActive = false;
      let questionSelectRootOverlayFrame = 0;
      let questionLastPointerClient = { x: 0, y: 0 };
      let questionWaitNoticeNode = null;
      let questionTypingSkipPortalButton = null;
      let questionTypingRootTopPadding = null;
      let questionTypingRootReservedHeight = null;
      let questionRootScrollbarHideTimer = 0;
      let questionCardOnlyViewToken = 0;
      let questionMobileActivePanel = "root";
      let questionMobilePanelObserver = null;
      let questionMobilePanelSyncFrame = 0;
      const questionInputAutoFocusTimers = new Set();
      const questionCardOnlyViewTimers = new Set();
      const questionCardRevealTimers = new Set();
      let questionTypingFullText = "";
      let questionTypingCometNode = null;
      let questionPictureZoom = 1;
      const QUESTION_CAMERA_PAN_SETTLE_MS = 920;
      const QUESTION_HIGHLIGHT_PAN_SETTLE_MS = 1700;
      const QUESTION_HIGHLIGHT_PAN_BEFORE_SCAN_DELAY_MS = 1000;
      const QUESTION_CARD_REVEAL_SETTLE_MS = 2000;
      const QUESTION_ROOT_HIGHLIGHT_SETTLE_MS = 3000;
      const QUESTION_HIGHLIGHT_RETURN_DELAY_MS = 1000;
      const QUESTION_HIGHLIGHT_RETURN_PAN_MS = 1300;
      const QUESTION_CARD_PROMPT_SCAN_MS = 860;
      const QUESTION_CARD_CHOICE_REVEAL_STEP_MS = 150;
      const QUESTION_ROOT_OPEN_TYPING_DELAY_MS = 2000;
      const QUESTION_ROOT_TOP_SCREEN_GAP = 20;
      const QUESTION_ROOT_BASE_WIDTH = 760;
      const QUESTION_CARD_EXIT_MS = 660;
      const QUESTION_INPUT_ACCENT = { rgb: "108, 240, 164", color: "#6cf0a4" };
      const QUESTION_ROOT_NOTICE_AFTER_MS = 1000;
      const QUESTION_ROOT_NOTICE_BOOT_MS = 760;
      const QUESTION_ROOT_NOTICE_HIDE_MS = 380;
      const QUESTION_ROOT_NOTICE_VOICE_DELAY_MS = 2000;
      const QUESTION_ANIMATION_ENERGY_SEGMENT_MS = 1180;
      const QUESTION_ANIMATION_ENERGY_SEGMENT_DELAY_MS = 54;
      const QUESTION_ANIMATION_ENERGY_SETTLE_MS = 140;
      const QUESTION_ANIMATION_ENERGY_DISCHARGE_MS = 760;
      const QUESTION_ANIMATION_ENERGY_DISCHARGE_DELAY_MS = 36;
      const QUESTION_ANIMATION_ENERGY_DISCHARGE_SETTLE_MS = 80;
      const QUESTION_ANIMATION_ENERGY_SHOCK_MS = 560;
      const QUESTION_INFO_CARD_REVEAL_MS = 680;
      const QUESTION_INFO_CARD_HIDE_MS = 380;
      const QUESTION_PICTURE_REGION_DEFAULT_COLOR = "#ff8a3d";
      const QUESTION_INPUT_DEFAULT_TEXT_COLOR = "#7eebff";
      const safeQuestionHexColor = (color, fallback = QUESTION_INPUT_DEFAULT_TEXT_COLOR) => {
        const value = clean(color);
        if (/^#[0-9a-f]{6}$/i.test(value)) {
          return value.toLowerCase();
        }
        if (/^#[0-9a-f]{3}$/i.test(value)) {
          return `#${value[1]}${value[1]}${value[2]}${value[2]}${value[3]}${value[3]}`.toLowerCase();
        }
        return fallback;
      };
      const questionBool = (value) => {
        if (typeof value === "boolean") {
          return value;
        }
        if (typeof value === "number") {
          return value !== 0;
        }
        const text = clean(value).toLowerCase();
        if (["1", "true", "yes", "y", "on"].includes(text)) {
          return true;
        }
        if (["0", "false", "no", "n", "off"].includes(text)) {
          return false;
        }
        return Boolean(value);
      };
      const safeQuestionPictureRegionColor = (color) => {
        const value = clean(color);
        if (/^#[0-9a-f]{6}$/i.test(value)) {
          return value.toLowerCase();
        }
        if (/^#[0-9a-f]{3}$/i.test(value)) {
          return `#${value[1]}${value[1]}${value[2]}${value[2]}${value[3]}${value[3]}`.toLowerCase();
        }
        return QUESTION_PICTURE_REGION_DEFAULT_COLOR;
      };
      const optionalQuestionPictureRegionColor = (color) => {
        const value = clean(color);
        if (/^#[0-9a-f]{6}$/i.test(value)) {
          return value.toLowerCase();
        }
        if (/^#[0-9a-f]{3}$/i.test(value)) {
          return `#${value[1]}${value[1]}${value[2]}${value[2]}${value[3]}${value[3]}`.toLowerCase();
        }
        return "";
      };
      const questionColorToRgb = (color, fallback = QUESTION_PICTURE_REGION_DEFAULT_COLOR) => {
        const hex = safeQuestionPictureRegionColor(color || fallback).slice(1);
        return [
          Number.parseInt(hex.slice(0, 2), 16),
          Number.parseInt(hex.slice(2, 4), 16),
          Number.parseInt(hex.slice(4, 6), 16),
        ].map((value) => Number.isFinite(value) ? value : 255);
      };
      let questionCameraTransform = "";
      let questionResponsiveScale = 1;
      let questionAudio = null;
      let questionInfoTypingTimer = 0;
      let questionInfoRevealTimer = 0;
      let questionInfoRevealResolve = null;
      let questionInfoRevealPromise = null;
      let questionInfoHideTimer = 0;
      let questionInfoAudioClip = null;
      let questionRootNoticeTypingTimer = 0;
      let questionRootNoticeTypingToken = 0;
      let questionRootNoticeAudio = null;
      let questionRootNoticeCompletionTimer = 0;
      let questionRootNoticeBootTimer = 0;
      let questionRootNoticeVoiceDelayTimer = 0;
      let questionRootNoticeVoiceDelayResolve = null;
      let questionRootNoticePendingFinish = null;
      let questionRootInfoCard = null;
      let questionRootInfoConnector = null;
      let questionRootInfoExtraConnectors = [];
      let questionRootInfoTypingTimer = 0;
      let questionRootInfoActiveAnchor = null;
      let questionRootInfoActivePayload = null;
      let questionRootHoverInfoCard = null;
      let questionRootHoverInfoConnector = null;
      let questionRootHoverInfoTypingTimer = 0;
      let questionPictureRegionLayer = null;
      let questionSelectConnectorLayer = null;
      let questionPictureAnswerLayer = null;
      let questionPictureAnswerConnectors = [];
      let questionPictureAnswerActive = false;
      let questionPictureAnswerPreparedItem = null;
      let questionPictureAnswerOptionValues = [];
      let questionPictureRegionPromptLocked = false;
      let questionPictureAnswerFeedbackNode = null;
      let questionPicturePromptFeedbackTimer = 0;
      let questionPicturePromptFeedbackToken = 0;
      let questionGuidanceBranchNodes = [];
      let questionGuidanceRelayoutFrame = 0;
      let questionGuidanceSettleToken = 0;
      let questionMobilePicturePager = null;
      let questionMobilePicturePage = "answers";
      let questionMobileGuidanceStack = [];
      const questionGuidanceNodeMap = new Map();
      const questionGuidanceHoverTimers = new WeakMap();
      const questionGuidanceCloseTimers = new Map();
      const questionGuidanceUnlockedPaths = new Set();
      const questionGuidanceUnlockedAnswerIndex = new Map();
      const questionGuidanceUnlockedAnswerValue = new Map();
      const questionGuidancePinnedPaths = new Set();
      const questionCrystalAwardedKeys = new Set();
      let currentMissionCrystalAwards = {};
      let questionRewardConfig = {
        crystal: {
          id: "crystal",
          name: "Prism Crystal",
          use: "Stores learning energy for future item upgrades.",
        },
      };
      let questionInventoryState = null;
      let questionInventorySyncBusy = false;
      let questionInventorySyncTimer = 0;
      let questionInventoryHud = null;
      let questionInventoryHudTimer = 0;
      let questionInventoryHudPreviewItem = null;
      let questionCameraScrollFrame = 0;
      let questionCameraScrollToken = 0;
      let questionSideLayoutFrame = 0;
      let questionSideLayoutFollowFrame = 0;
      let questionResizeLayoutTimer = 0;
      let questionResizeLayoutLastAt = 0;
      let questionSideLayoutCacheKey = "";
      let questionConnectorFocusTimer = 0;
      let questionRootFocusTimer = 0;
      const questionCardFxTimers = new WeakMap();
      let questionLastPictureSkin = 0;
      let questionLastShipIndex = 0;
      let spaceNavigatorNode = null;
      let spaceNavigatorPointerId = 0;
      let spaceNavigatorVector = { x: 0, y: 0, power: 0 };
      let spaceNavigatorVisualVector = { x: 0, y: 0, power: 0 };
      let spaceNavigatorVelocity = { x: 0, y: 0 };
      let spaceNavigatorFrame = 0;
      let spaceNavigatorLastTick = 0;
      let spaceNavigatorObserver = null;
      let spaceNavigatorNearPointer = false;
      let spaceKeyboardNavigatorKeys = new Set();
      let spaceKeyboardNavigatorFrame = 0;
      let spaceKeyboardNavigatorLastTick = 0;
      let spaceKeyboardNavigatorVelocity = { x: 0, y: 0 };
      let vocabShuffleRoundPulsePending = false;
      let grammarState = { active: false, items: [], index: 0, lock: false, pendingMessage: "Chính xác.", revision: 0, shuffleSeed: "", awaitingStart: false, started: false };
      let grammarFirstAttempted = new Set();
      let grammarFirstTryCorrect = new Set();
      let grammarFocusRange = null;
      let grammarEffectTimer = 0;
      let activeGrammarAudio = null;
      let grammarAudioStopToken = 0;
      const REQUIRED_FULL_LISTENS = 3;
      const REVIEW_REQUIRED_LISTENS = 1;
      const SPEAK_UNLOCK_SCORE = 50;
      const VOCAB_BATCH_SIZE = 5;
      const VOCAB_REGISTRY_RENDER_LIMIT = 80;
      const VOCAB_AUDIO_LOOKAHEAD = 2;
      const IPA_STAR_FULL_LISTENS = 10;
      const DEFAULT_WORD_HINT_IDLE_MS = 30000;
      const DEFAULT_Q_ROOT_HUD_LINES = [
        "MISSION NODE ONLINE",
        "ORBITAL MEMORY LINK",
        "QUESTION SIGNAL READY",
      ];
      const VOCAB_AUDIO_PRELOAD_WORKERS = 2;
      const cachedAudioClipUrls = new Map();
      const pendingAudioClipPreloads = new Map();
      let wordHintIdleMs = DEFAULT_WORD_HINT_IDLE_MS;
      let paragraphHintIdleSeconds = DEFAULT_WORD_HINT_IDLE_MS / 1000;
      let qRootHudLineValues = [...DEFAULT_Q_ROOT_HUD_LINES];

      const ftDebugElementLabel = (node) => {
        if (!node || !node.nodeType) {
          return "";
        }
        const id = node.id ? `#${node.id}` : "";
        const className = typeof node.className === "string"
          ? node.className.trim().replace(/\s+/g, ".")
          : "";
        return `${String(node.tagName || node.nodeName || "").toLowerCase()}${id}${className ? "." + className : ""}`;
      };

      const collectFtCpuDebug = (options = {}) => {
        const animations = typeof document.getAnimations === "function"
          ? document.getAnimations({ subtree: true })
          : [];
        const animationRows = animations.map((animation) => {
          const effect = animation.effect || null;
          const target = effect && effect.target || null;
          let timing = {};
          try {
            timing = effect && typeof effect.getComputedTiming === "function" ? effect.getComputedTiming() : {};
          } catch (error) {
            timing = {};
          }
          return {
            name: animation.animationName || "",
            state: animation.playState || "",
            target: ftDebugElementLabel(target),
            duration: Number(timing.duration || 0),
            iterations: timing.iterations,
            current: Math.round(Number(animation.currentTime || 0)),
          };
        });
        const runningAnimations = animationRows.filter((row) => row.state === "running");
        const infiniteAnimations = runningAnimations.filter((row) => row.iterations === Infinity || row.iterations === "Infinity");
        const debug = {
          question: {
            active: Boolean(questionModeActive),
            settled: Boolean(questionCardsRevealSettled),
            revealAnimating: Boolean(questionRevealAnimationsActive),
            idleStatic: Boolean(stageNode && stageNode.classList.contains("is-question-idle-static")),
            stageClass: stageNode ? stageNode.className : "",
            rootClass: qRootCard ? qRootCard.className : "",
            activeFxCards: shellNode ? shellNode.querySelectorAll(".is-card-fx-active").length : 0,
            hoveredFxCards: shellNode ? shellNode.querySelectorAll(".is-card-fx-hover").length : 0,
            focusedConnectors: shellNode ? shellNode.querySelectorAll(".is-connector-focused, .is-focused").length : 0,
            pictureConnectorHovering: Boolean(shellNode && shellNode.classList.contains("is-picture-card-hovering")),
            effectsPaused: Boolean(questionCardEffectsPaused),
            animationPaused: Boolean(questionAnimationsPaused),
            debugPaused: document.documentElement.classList.contains("ft-debug-animations-paused"),
            currentNode: questionCurrentNode && (questionCurrentNode.id || questionCurrentNode.root || ""),
          },
          timers: {
            questionTypingTimer: Boolean(questionTypingTimer),
            questionRevealTimer: Boolean(questionRevealTimer),
            questionCameraScrollFrame: Boolean(questionCameraScrollFrame),
            questionSideLayoutFrame: Boolean(questionSideLayoutFrame),
            questionSideLayoutFollowFrame: Boolean(questionSideLayoutFollowFrame),
            questionResizeLayoutTimer: Boolean(questionResizeLayoutTimer),
            questionInfoTypingTimer: Boolean(questionInfoTypingTimer),
            questionRootInfoTypingTimer: Boolean(questionRootInfoTypingTimer),
            questionRootHoverInfoTypingTimer: Boolean(questionRootHoverInfoTypingTimer),
            questionPicturePromptFeedbackTimer: Boolean(questionPicturePromptFeedbackTimer),
            spaceNavigatorFrame: Boolean(spaceNavigatorFrame),
            spaceKeyboardNavigatorFrame: Boolean(spaceKeyboardNavigatorFrame),
            learnerChatPollTimer: Boolean(learnerChatPollTimer),
            learnerStreamPollTimer: Boolean(learnerStreamPollTimer),
            learnerScreenPollTimer: Boolean(learnerScreenPollTimer),
            learnerScreenFrameTimer: Boolean(learnerScreenFrameTimer),
            learnerScreenControlPollTimer: Boolean(learnerScreenControlPollTimer),
            learnerPaintPollTimer: Boolean(learnerPaintPollTimer),
            authSessionMonitorTimer: Boolean(authSessionMonitorTimer),
          },
          screen: {
            previewFramesEnabled: Boolean(LEARNER_SCREEN_PREVIEW_FRAMES_ENABLED),
            previewTargetFps: LEARNER_SCREEN_PREVIEW_TARGET_FPS,
            previewIntervalMs: LEARNER_SCREEN_PREVIEW_INTERVAL_MS,
            previewBinaryEnabled: Boolean(learnerScreenBinaryFrameEnabled),
            sessionState: learnerScreenSession && learnerScreenSession.state || "",
            captureActive: Boolean(learnerScreenCaptureStream),
            audioTracks: learnerScreenCaptureStream ? screenAudioTracks(learnerScreenCaptureStream).length : 0,
            audioRelayRecording: Boolean(learnerScreenAudioRecorder && learnerScreenAudioRecorder.state === "recording"),
            sendingFrame: Boolean(learnerScreenSending),
            lastFrameMode: learnerScreenFrameLastMode,
            lastFrameElapsedMs: Math.round(learnerScreenFrameLastElapsedMs),
            lastFrameEncodeMs: Math.round(learnerScreenFrameLastEncodeMs),
            lastFrameUploadMs: Math.round(learnerScreenFrameLastUploadMs),
            lastFrameBytes: Number(learnerScreenFrameLastBytes || 0),
            peerState: learnerScreenPeer && learnerScreenPeer.connectionState || "",
          },
          animations: {
            total: animationRows.length,
            running: runningAnimations.length,
            infiniteRunning: infiniteAnimations.length,
            topRunning: runningAnimations.slice(0, 60),
          },
        };
        if (!options || options.log !== false) {
          try {
            console.log("[ft cpu debug]", debug);
            if (console.table) {
              console.table(debug.animations.topRunning);
            }
          } catch (error) {
          }
        }
        return debug;
      };

      window.__ftCpuDebug = collectFtCpuDebug;
      window.__ftPauseAllAnimations = () => {
        document.documentElement.classList.add("ft-debug-animations-paused");
        const animations = typeof document.getAnimations === "function"
          ? document.getAnimations({ subtree: true })
          : [];
        return animations.length;
      };
      window.__ftResumeAllAnimations = () => {
        document.documentElement.classList.remove("ft-debug-animations-paused");
        const animations = typeof document.getAnimations === "function"
          ? document.getAnimations({ subtree: true })
          : [];
        return animations.length;
      };
      window.__ftSetPerfSafeMode = (enabled = true) => {
        const active = Boolean(enabled);
        document.documentElement.classList.toggle("ft-perf-safe", active);
        return collectFtCpuDebug();
      };

      let ftCpuDebugPanel = null;
      let ftCpuDebugTimer = 0;

      const ftCpuDebugBoolList = (items = {}) => Object.entries(items)
        .filter(([, value]) => Boolean(value))
        .map(([key]) => key);

      const formatFtCpuDebug = (debug = {}) => {
        const question = debug.question || {};
        const timers = ftCpuDebugBoolList(debug.timers || {});
        const animations = debug.animations || {};
        const screen = debug.screen || {};
        const topRunning = Array.isArray(animations.topRunning) ? animations.topRunning.slice(0, 14) : [];
        const lines = [
          `time: ${new Date().toLocaleTimeString()}`,
          `question: active=${Boolean(question.active)} settled=${Boolean(question.settled)} idleStatic=${Boolean(question.idleStatic)} reveal=${Boolean(question.revealAnimating)}`,
          `fx: paused=${Boolean(question.effectsPaused)} activeCards=${question.activeFxCards || 0} hoveredCards=${question.hoveredFxCards || 0} focused=${question.focusedConnectors || 0} pictureHover=${Boolean(question.pictureConnectorHovering)}`,
          `animation: switchPaused=${Boolean(question.animationPaused)} debugPaused=${Boolean(question.debugPaused)}`,
          `animations: total=${animations.total || 0} running=${animations.running || 0} infiniteRunning=${animations.infiniteRunning || 0}`,
          `timers: ${timers.length ? timers.join(", ") : "none"}`,
          `screen: state=${screen.sessionState || "none"} capture=${Boolean(screen.captureActive)} sending=${Boolean(screen.sendingFrame)} peer=${screen.peerState || "none"}`,
          "",
          "top running animations:",
          ...(topRunning.length
            ? topRunning.map((row, index) => `${index + 1}. ${row.name || "(unnamed)"} | ${row.target || "(no target)"} | ${row.iterations}x | ${row.duration}ms`)
            : ["none"]),
        ];
        return lines.join("\n");
      };

      const updateFtCpuDebugPanel = () => {
        if (!ftCpuDebugPanel || ftCpuDebugPanel.classList.contains("is-hidden")) {
          return null;
        }
        const body = ftCpuDebugPanel.querySelector(".ft-cpu-debug-body");
        const debug = collectFtCpuDebug({ log: false });
        if (body) {
          body.textContent = formatFtCpuDebug(debug);
        }
        return debug;
      };

      const stopFtCpuDebugPanelTimer = () => {
        if (ftCpuDebugTimer) {
          window.clearInterval(ftCpuDebugTimer);
          ftCpuDebugTimer = 0;
        }
      };

      const ensureFtCpuDebugPanel = () => {
        if (ftCpuDebugPanel) {
          return ftCpuDebugPanel;
        }
        ftCpuDebugPanel = document.createElement("section");
        ftCpuDebugPanel.className = "ft-cpu-debug-panel is-hidden";
        ftCpuDebugPanel.setAttribute("aria-label", "CPU debug");
        ftCpuDebugPanel.innerHTML = [
          '<div class="ft-cpu-debug-head">',
          '<div class="ft-cpu-debug-title">Space_Q CPU Debug</div>',
          '<button type="button" data-ft-cpu-action="refresh">Refresh</button>',
          '<button type="button" data-ft-cpu-action="pause">Pause anim</button>',
          '<button type="button" data-ft-cpu-action="resume">Resume anim</button>',
          '<button type="button" data-ft-cpu-action="safe">Safe mode</button>',
          '<button type="button" data-ft-cpu-action="close">Close</button>',
          '</div>',
          '<pre class="ft-cpu-debug-body">Waiting...</pre>',
        ].join("");
        ftCpuDebugPanel.addEventListener("click", (event) => {
          const button = event.target && event.target.closest ? event.target.closest("[data-ft-cpu-action]") : null;
          if (!button) {
            return;
          }
          const action = button.getAttribute("data-ft-cpu-action") || "";
          if (action === "refresh") {
            updateFtCpuDebugPanel();
          } else if (action === "pause") {
            window.__ftPauseAllAnimations();
            updateFtCpuDebugPanel();
          } else if (action === "resume") {
            document.documentElement.classList.remove("ft-perf-safe");
            window.__ftResumeAllAnimations();
            updateFtCpuDebugPanel();
          } else if (action === "safe") {
            window.__ftSetPerfSafeMode(!document.documentElement.classList.contains("ft-perf-safe"));
            updateFtCpuDebugPanel();
          } else if (action === "close") {
            ftCpuDebugPanel.classList.add("is-hidden");
            stopFtCpuDebugPanelTimer();
          }
        });
        document.body.appendChild(ftCpuDebugPanel);
        return ftCpuDebugPanel;
      };

      window.__ftShowCpuDebug = (enabled = true) => {
        const panel = ensureFtCpuDebugPanel();
        const active = Boolean(enabled);
        panel.classList.toggle("is-hidden", !active);
        stopFtCpuDebugPanelTimer();
        if (active) {
          updateFtCpuDebugPanel();
          ftCpuDebugTimer = window.setInterval(updateFtCpuDebugPanel, 3000);
        }
        return active ? collectFtCpuDebug({ log: false }) : null;
      };

      if (params.get("ft_debug") === "1" || params.get("ft_cpu_debug") === "1" || window.__FTG_PREVIEW_DEBUG__) {
        window.setTimeout(() => window.__ftShowCpuDebug(true), 1600);
      }

      let completedListenCount = 0;
      let nextPanelCanShow = false;
      let nextAttentionTimer = 0;
      let speakStepCompleted = false;
      let speakStarCount = 0;
      let grammarStepCompleted = false;
      let reviewModeActive = false;
      let reviewQueue = [];
      let reviewMasteredIndexes = new Set();
      let reviewCurrentHadError = false;
      let reviewSpeakCompleted = false;
      let speakSkipPollTimer = 0;
      let speakSkipRequestPending = false;
      const createSpaceWSpeakSkipSessionId = () => {
        try {
          if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
          }
        } catch (error) {
        }
        return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
      };
      let spaceWSpeakSkipSessionId = createSpaceWSpeakSkipSessionId();
      let spaceWSpeakSkipSessionApproved = false;
      let reviewFinished = false;
      let lessonEffects = {};
      let previousWordOk = [];
      let pendingSpaceWordCheck = false;
      let lastFalseWordKey = "";
      let wordHintTimer = 0;
      let wordHintTickTimer = 0;
      let wordHintDeadline = 0;
      let wordHintWatchKey = "";
      let wordTimeoutHintKey = "";
      let wordHintedKeys = new Set();
      let translateKeyboardPinUntil = 0;
      let translateKeyboardPinFrame = 0;
      let vocabKeyboardPinUntil = 0;
      let vocabKeyboardPinFrame = 0;
      let vocabKeyboardPinOptions = {};
      let mobileInfiniteMotionFrame = 0;
      let mobileInfiniteMotionSyncTimer = 0;
      let mobileInfiniteMotionObserver = null;
      const mobilePausedInfiniteAnimations = new Set();
      const MOBILE_ANIMATION_STORAGE_KEY = "future_mobile_animation_enabled";
      const defaultLearnerAnimationEnabled = () => {
        try {
          return !window.matchMedia("(max-width: 760px), (pointer: coarse)").matches;
        } catch (error) {
          return true;
        }
      };
      const readMobileAnimationEnabled = () => {
        try {
          const saved = localStorage.getItem(MOBILE_ANIMATION_STORAGE_KEY);
          if (saved === "1" || saved === "true" || saved === "on") {
            return true;
          }
          if (saved === "0" || saved === "false" || saved === "off") {
            return false;
          }
        } catch (error) {
        }
        return defaultLearnerAnimationEnabled();
      };
      let mobileAnimationEnabled = readMobileAnimationEnabled();
      let animationEngineBootTimer = 0;
      let animationEngineEnableTimer = 0;
      let grammarKeepSilent = false;
      let mobileActivePanelKey = "";
      const mobileUnlockedPanels = new Set();
      const soundOfTextVoices = [
        ["SOT | Female UK", "en-GB"],
        ["SOT | Female US", "en-US"],
      ];
      const edgeVoiceDefaults = [
        { label: "Edge | English US | Aria", name: "en-US-AriaNeural", locale: "en-US", gender: "Female" },
        { label: "Edge | English US | Guy", name: "en-US-GuyNeural", locale: "en-US", gender: "Male" },
        { label: "Edge | English US | Jenny", name: "en-US-JennyNeural", locale: "en-US", gender: "Female" },
        { label: "Edge | English US | Davis", name: "en-US-DavisNeural", locale: "en-US", gender: "Male" },
        { label: "Edge | English GB | Sonia", name: "en-GB-SoniaNeural", locale: "en-GB", gender: "Female" },
        { label: "Edge | English GB | Ryan", name: "en-GB-RyanNeural", locale: "en-GB", gender: "Male" },
      ];
      let edgeVoices = edgeVoiceDefaults.slice();
      const accepted = [answer]
        .concat((params.get("accept") || "").split("|"))
        .map(normalize)
        .filter(Boolean);

      questionNode.textContent = question;
      englishNode.textContent = answer;
      ipaNode.textContent = ipa;

      const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
      const isMobilePanelFlow = () => window.matchMedia("(max-width: 600px), (pointer: coarse)").matches;
      const setSpaceWModeClass = (active) => {
        const enabled = Boolean(active);
        document.documentElement.classList.toggle("ft-space-w-mode", enabled);
        if (enabled) {
          document.documentElement.classList.remove("ft-space-v-mode");
          document.documentElement.classList.remove("ft-vocab-mobile-pin");
        }
        if (stageNode) {
          stageNode.classList.toggle("is-space-w-mode", enabled);
          if (enabled) {
            stageNode.classList.remove("is-space-v-mode");
            stageNode.classList.remove("is-vocab-mobile-pin");
            stageNode.scrollLeft = 0;
          }
        }
        if (enabled && shellNode) {
          shellNode.classList.remove("is-vocab-mobile-pin");
        }
        if (!enabled) {
          return;
        }
        try {
          const doc = document.scrollingElement || document.documentElement;
          if (doc) {
            doc.scrollLeft = 0;
          }
          document.documentElement.scrollLeft = 0;
          if (document.body) {
            document.body.scrollLeft = 0;
          }
        } catch (error) {
          // Horizontal rubber-band cleanup is best-effort across mobile browsers.
        }
      };
      const clampSpaceWHorizontalScroll = () => {
        if (!document.documentElement.classList.contains("ft-space-w-mode")) {
          return;
        }
        try {
          const doc = document.scrollingElement || document.documentElement;
          if (stageNode && stageNode.scrollLeft) {
            stageNode.scrollLeft = 0;
          }
          if (doc && doc.scrollLeft) {
            doc.scrollLeft = 0;
          }
          if (document.documentElement.scrollLeft) {
            document.documentElement.scrollLeft = 0;
          }
          if (document.body && document.body.scrollLeft) {
            document.body.scrollLeft = 0;
          }
        } catch (error) {
          // Some embedded mobile browsers expose scrollLeft inconsistently.
        }
      };
      window.addEventListener("scroll", clampSpaceWHorizontalScroll, { passive: true });
      window.addEventListener("resize", clampSpaceWHorizontalScroll, { passive: true });
      if (stageNode) {
        stageNode.addEventListener("scroll", clampSpaceWHorizontalScroll, { passive: true });
      }

      const setAnswerEntryLocked = (locked, options = {}) => {
        const shouldLock = Boolean(locked) && (Boolean(options && options.force) || !isMobilePanelFlow());
        answerInput.disabled = shouldLock;
        if (checkButton) {
          checkButton.disabled = shouldLock;
        }
        if (shouldLock) {
          stopWordHintWatch();
        }
        if (answerInputWrap) {
          answerInputWrap.classList.toggle("is-locked", shouldLock);
        }
      };

      const connectorForPanel = (panel) => {
        if (panel === speakPanel) {
          return speakConnector;
        }
        if (panel === scorePanel) {
          return scoreConnector;
        }
        if (panel === hintPanel) {
          return hintConnector;
        }
        if (panel === aboutPanel) {
          return aboutConnector;
        }
        if (panel === grammarPanel) {
          return grammarConnector;
        }
        return ipaConnector;
      };

      const allPanelConnectors = () => [speakConnector, scoreConnector, hintConnector, aboutConnector, grammarConnector, ipaConnector].filter(Boolean);
      const allPanels = () => [speakPanel, scorePanel, hintPanel, aboutPanel, grammarPanel, ipaPanel].filter(Boolean);
      const mobilePanelEntries = () => [
        ["score", scorePanel],
        ["hint", hintPanel],
        ["about", aboutPanel],
        ["ipa", ipaPanel],
        ["speak", speakPanel],
        ["grammar", grammarPanel],
      ];
      const mobilePanelKeys = new Set(["score", "hint", "about", "ipa", "speak", "grammar"]);
      const isPhonePanelTabs = () => window.matchMedia("(max-width: 760px)").matches;
      const mobilePanelForKey = (key) => {
        const found = mobilePanelEntries().find(([itemKey]) => itemKey === key);
        return found ? found[1] : null;
      };
      const mobileHintAboutTabKey = () => {
        const hintLive = Boolean(hintPanel && hintPanel.classList.contains("is-live") && mobileUnlockedPanels.has("hint"));
        const aboutLive = Boolean(aboutPanel && aboutPanel.classList.contains("is-live") && mobileUnlockedPanels.has("about"));
        if (mobileActivePanelKey === "about" && aboutLive) {
          return "about";
        }
        if (mobileActivePanelKey === "hint" && hintLive) {
          return "hint";
        }
        if (aboutLive && !hintLive) {
          return "about";
        }
        return "hint";
      };
      const mobileTabTargetKey = (key) => (key === "hint" ? mobileHintAboutTabKey() : key);
      const setMobilePanelUnlocked = (key, unlocked = true) => {
        if (!key) {
          return;
        }
        if (unlocked) {
          mobileUnlockedPanels.add(key);
        } else {
          mobileUnlockedPanels.delete(key);
          if (mobileActivePanelKey === key) {
            mobileActivePanelKey = "";
          }
        }
      };

      const setVocabModeClass = (active) => {
        const enabled = Boolean(active);
        document.documentElement.classList.toggle("ft-space-v-mode", enabled);
        if (stageNode) {
          stageNode.classList.toggle("is-space-v-mode", enabled);
        }
      };
      const syncMobilePanelTabs = () => {
        const phoneMode = isPhonePanelTabs();
        if (phoneMode && mobileActivePanelKey) {
          const activePanel = mobilePanelForKey(mobileActivePanelKey);
          if (!mobileUnlockedPanels.has(mobileActivePanelKey) || !activePanel || !activePanel.classList.contains("is-live")) {
            mobileActivePanelKey = "";
          }
        }
        if (phoneMode && nextPanelCanShow && mobileActivePanelKey === "score") {
          mobileActivePanelKey = "";
        }
        mobilePanelEntries().forEach(([key, panel]) => {
          if (!panel) {
            return;
          }
          const live = panel.classList.contains("is-live");
          const hidden = phoneMode && live && (!mobileActivePanelKey || mobileActivePanelKey !== key);
          panel.classList.toggle("is-mobile-hidden", hidden);
        });
        mobileTabButtons.forEach((button) => {
          const rawKey = button.dataset.panel || "";
          const key = mobileTabTargetKey(rawKey);
          const hideScore = Boolean(phoneMode && rawKey === "score" && nextPanelCanShow);
          button.hidden = hideScore;
          if (hideScore) {
            button.disabled = true;
            button.classList.remove("is-active");
            button.setAttribute("aria-pressed", "false");
            return;
          }
          if (rawKey === "hint") {
            button.textContent = key === "about" ? "About" : "Hint";
          }
          const panel = mobilePanelForKey(key);
          const live = Boolean(panel && panel.classList.contains("is-live"));
          const enabled = mobileUnlockedPanels.has(key) && live;
          button.disabled = !enabled;
          button.classList.toggle("is-active", phoneMode && enabled && mobileActivePanelKey === key);
          button.setAttribute("aria-pressed", phoneMode && enabled && mobileActivePanelKey === key ? "true" : "false");
        });
      };
      const mobileStaticMotionSurface = () => window.matchMedia("(max-width: 760px), (pointer: coarse)").matches;
