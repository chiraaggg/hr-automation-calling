def parse_candidate_response(transcript: str):
    # Example regex-based parsing; you can improve with OpenAI API
    candidate = {}
    if "CTC" in transcript:
        candidate["current_ctc"] = "Extracted from transcript"
    if "expected" in transcript:
        candidate["expected_ctc"] = "Extracted from transcript"
    if "experience" in transcript:
        candidate["experience"] = "Extracted from transcript"
    if "skills" in transcript:
        candidate["skills"] = ["Python", "SQL"]  # example
    return candidate
