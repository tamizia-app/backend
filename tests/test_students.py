def test_create_student_inside_classroom(client, teacher_headers):
    classroom_response = client.post(
        "/api/v1/classrooms",
        headers=teacher_headers,
        json={"name": "2C", "grade_level": "segundo", "section": "C", "school_year": "2026-01-01"},
    )
    classroom_id = classroom_response.json()["classroom_id"]

    student_response = client.post(
        f"/api/v1/classrooms/{classroom_id}/students",
        headers=teacher_headers,
        json={"code": "ST-001", "age": 7, "gender": "GIRL"},
    )
    assert student_response.status_code == 201
    student = student_response.json()
    assert student["code"] == "ST-001"

    list_response = client.get(f"/api/v1/classrooms/{classroom_id}/students", headers=teacher_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
