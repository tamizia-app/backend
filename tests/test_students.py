def test_create_student_inside_classroom(client, teacher_headers):
    classroom_response = client.post(
        "/api/v1/classrooms",
        headers=teacher_headers,
        json={"name": "2C", "grade_level": "2", "section": "C", "school_year": "2026"},
    )
    classroom_id = classroom_response.json()["id"]

    student_response = client.post(
        f"/api/v1/classrooms/{classroom_id}/students",
        headers=teacher_headers,
        json={"code": "ST-001", "first_name": "Ana", "last_name": "Lopez", "age": 7},
    )
    assert student_response.status_code == 201
    student = student_response.json()
    assert student["code"] == "ST-001"

    list_response = client.get(f"/api/v1/classrooms/{classroom_id}/students", headers=teacher_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
