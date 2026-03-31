def test_session_flow_with_writing_and_reading_analysis(client, teacher_headers):
    classroom_response = client.post(
        "/api/v1/classrooms",
        headers=teacher_headers,
        json={"name": "1A", "grade_level": "1", "section": "A", "school_year": "2026"},
    )
    classroom_id = classroom_response.json()["id"]
    student_response = client.post(
        f"/api/v1/classrooms/{classroom_id}/students",
        headers=teacher_headers,
        json={"code": "ST-101", "first_name": "Luis", "last_name": "Perez", "age": 6},
    )
    student_id = student_response.json()["id"]

    session_response = client.post(
        "/api/v1/sessions",
        headers=teacher_headers,
        json={"student_id": student_id, "exercise_id": "11111111-1111-1111-1111-111111111111"},
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]

    start_response = client.patch(f"/api/v1/sessions/{session_id}/start", headers=teacher_headers)
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "in_progress"

    writing_response = client.post(
        f"/api/v1/sessions/{session_id}/writing-sample",
        headers=teacher_headers,
        files={"file": ("sample.png", b"fake-image-content", "image/png")},
        data={"source_type": "handwritten", "stroke_count": "12", "correction_count": "1", "duration_seconds": "25"},
    )
    assert writing_response.status_code == 201

    analyze_writing_response = client.post(f"/api/v1/sessions/{session_id}/analyze-writing", headers=teacher_headers)
    assert analyze_writing_response.status_code == 200
    assert analyze_writing_response.json()["analysis"]["extracted_text"] == "Mi casa tiene una ventana azul."
    assert analyze_writing_response.json()["writing_score"] == 100.0

    audio_response = client.post(
        f"/api/v1/sessions/{session_id}/audio-sample",
        headers=teacher_headers,
        files={"file": ("sample.wav", b"fake-audio-content", "audio/wav")},
        data={"locale": "es-CO", "duration_seconds": "18"},
    )
    assert audio_response.status_code == 201

    analyze_reading_response = client.post(f"/api/v1/sessions/{session_id}/analyze-reading", headers=teacher_headers)
    assert analyze_reading_response.status_code == 200
    assert analyze_reading_response.json()["reading_score"] == 86.75

    result_response = client.post(f"/api/v1/sessions/{session_id}/generate-result", headers=teacher_headers)
    assert result_response.status_code == 200
    result_payload = result_response.json()["result"]
    assert result_payload["risk_flag"] == "LOW"
    assert result_payload["overall_score"] == 93.38

    complete_response = client.patch(f"/api/v1/sessions/{session_id}/complete", headers=teacher_headers)
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"

    detail_response = client.get(f"/api/v1/sessions/{session_id}", headers=teacher_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["result"]["risk_flag"] == "LOW"
