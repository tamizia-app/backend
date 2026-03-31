def test_teacher_can_create_and_list_own_classrooms(client, teacher_headers):
    create_response = client.post(
        "/api/v1/classrooms",
        headers=teacher_headers,
        json={"name": "3A", "grade_level": "3", "section": "A", "school_year": "2026"},
    )
    assert create_response.status_code == 201
    classroom = create_response.json()
    assert classroom["name"] == "3A"

    list_response = client.get("/api/v1/classrooms", headers=teacher_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_teacher_cannot_access_other_teacher_classroom(client, teacher_headers, other_teacher_headers):
    create_response = client.post(
        "/api/v1/classrooms",
        headers=teacher_headers,
        json={"name": "4B", "grade_level": "4", "section": "B", "school_year": "2026"},
    )
    classroom_id = create_response.json()["id"]

    other_response = client.get(f"/api/v1/classrooms/{classroom_id}", headers=other_teacher_headers)
    assert other_response.status_code == 404
