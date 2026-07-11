def build_transcript_event(speaker_id: str, utterance: str) -> dict[str, str]:
    return {"speaker_id": speaker_id, "utterance": utterance}
