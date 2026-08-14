from app import app


def test_dashboard_includes_repo_details_modal():
    client = app.test_client()
    response = client.get('/')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Edit repository details' in html
    assert 'Short description of this repository' in html
    assert 'Save changes' in html
