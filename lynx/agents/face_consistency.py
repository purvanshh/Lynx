from __future__ import annotations

from pathlib import Path

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.participant import Participant, WebcamFrame
from lynx.models.session import SessionState

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover - optional dependency
    mp = None


class FaceConsistencyAgent(BaseAgent):
    def __init__(self) -> None:
        self._detector = None
        if mp is not None:  # pragma: no branch
            self._detector = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=0.5,
            )

    @property
    def name(self) -> str:
        return "FaceConsistencyAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult | None:
        participant = next(
            participant for participant in session.participants if participant.participant_id == participant_id
        )
        if not participant.webcam_on:
            return None
        if not participant.webcam_frames:
            return AgentResult(
                agent=self.name,
                participant_id=participant.participant_id,
                score=0.5,
                weight=self.weight,
                reasoning="Webcam is on but no sampled frames are available yet. Face signal is neutral.",
            )

        face_counts = self._face_counts(participant)
        if not face_counts:
            return AgentResult(
                agent=self.name,
                participant_id=participant.participant_id,
                score=0.5,
                weight=self.weight,
                reasoning="Frames are present but no face counts could be derived. Face signal is neutral.",
            )

        total_frames = len(face_counts)
        valid_frames = sum(1 for count in face_counts if count == 1)
        no_face_frames = sum(1 for count in face_counts if count == 0)
        multi_face_frames = sum(1 for count in face_counts if count > 1)
        transitions = sum(
            1
            for previous, current in zip(face_counts, face_counts[1:], strict=False)
            if (previous == 0) != (current == 0)
        )

        score = valid_frames / total_frames
        if multi_face_frames:
            score = max(0.0, score - (0.3 * (multi_face_frames / total_frames)))
        if no_face_frames > total_frames * 0.3:
            score *= 0.7
        if transitions > 1:
            score = max(0.0, score - (0.1 * min(transitions, 3)))

        reasoning_parts = [f"Single-face frames {valid_frames}/{total_frames}"]
        if multi_face_frames:
            reasoning_parts.append(f"multiple faces in {multi_face_frames} frames")
        if no_face_frames:
            reasoning_parts.append(f"no face in {no_face_frames} frames")
        if transitions > 1:
            reasoning_parts.append(f"face presence toggled {transitions} times")

        return AgentResult(
            agent=self.name,
            participant_id=participant.participant_id,
            score=round(score, 3),
            weight=self.weight,
            reasoning=". ".join(reasoning_parts) + ".",
        )

    def _face_counts(self, participant: Participant) -> list[int]:
        counts: list[int] = []
        for frame in participant.webcam_frames:
            count = self._frame_face_count(frame)
            if count is not None:
                counts.append(count)
        return counts

    def _frame_face_count(self, frame: WebcamFrame) -> int | None:
        if frame.face_count is not None:
            return frame.face_count
        if self._detector is None or frame.image_path is None:
            return None

        image_path = Path(frame.image_path)
        if not image_path.exists():
            return None

        try:
            import cv2
        except ImportError:  # pragma: no cover - optional dependency
            return None

        image = cv2.imread(str(image_path))
        if image is None:
            return None
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self._detector.process(rgb_image)
        return len(results.detections) if results.detections else 0
