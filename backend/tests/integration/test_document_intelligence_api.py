"""Integration tests for the document-centric profile workflow."""
import fitz
from fastapi.testclient import TestClient

def pdf_bytes(text: str) -> bytes:
    document=fitz.open(); page=document.new_page(); page.insert_text((72,72),text); result=document.tobytes(); document.close(); return result

def test_document_upload_requires_authentication(client: TestClient):
    response=client.post('/api/documents/income_certificate/upload',files={'file':('income.pdf',b'%PDF-1.4','application/pdf')})
    assert response.status_code==401

def test_document_upload_rejects_duplicate_type(client: TestClient,auth_headers:dict):
    file=('income.pdf',pdf_bytes('Annual Income: 150000'),'application/pdf')
    assert client.post('/api/documents/income_certificate/upload',headers=auth_headers,files={'file':file}).status_code==201
    assert client.post('/api/documents/income_certificate/upload',headers=auth_headers,files={'file':file}).status_code==422

def test_document_replace_replaces_same_type_and_processes_new_file(client: TestClient,auth_headers:dict):
    first=pdf_bytes('Annual Income: 85000')
    second=pdf_bytes('Annual Income: 95000')
    uploaded=client.post('/api/documents/income_certificate/upload',headers=auth_headers,files={'file':('first.pdf',first,'application/pdf')})
    assert uploaded.status_code==201
    old_id=uploaded.json()['data']['id']
    replacement=client.post('/api/documents/income_certificate/upload',headers=auth_headers,data={'replace':'true'},files={'file':('second.pdf',second,'application/pdf')})
    assert replacement.status_code==201
    new_id=replacement.json()['data']['id']
    assert new_id != old_id
    assert client.post('/api/documents/process-all',headers=auth_headers).status_code==200
    extracted=client.get(f'/api/documents/extracted/{new_id}',headers=auth_headers)
    assert any(row['field_name']=='annual_income' and row['field_value']=='95000' for row in extracted.json()['data']['items'])

def test_process_preview_and_correct_document_profile(client: TestClient,auth_headers:dict):
    content=pdf_bytes('Name: Kumar\nAnnual Income: 150000\nCaste: BC\nCommunity: MBC')
    uploaded=client.post('/api/documents/income_certificate/upload',headers=auth_headers,files={'file':('income.pdf',content,'application/pdf')})
    assert uploaded.status_code==201; document_id=uploaded.json()['data']['id']
    processed=client.post('/api/documents/process-all',headers=auth_headers)
    assert processed.status_code==200 and processed.json()['data']['results'][0]['status']=='processed'
    extracted=client.get(f'/api/documents/extracted/{document_id}',headers=auth_headers)
    assert extracted.status_code==200 and any(x['field_name']=='annual_income' for x in extracted.json()['data']['items'])
    preview=client.get('/api/profile/preview',headers=auth_headers)
    assert preview.status_code==200 and preview.json()['data']['fields']['annual_income']=='150000'
    assert preview.json()['data']['needs_review']==0
    assert client.post('/api/profile/correct',headers=auth_headers,json={'field_name':'annual_income','value':'160000'}).status_code==200
    confirmed=client.post('/api/profile/confirm',headers=auth_headers)
    assert confirmed.status_code==200
    assert confirmed.json()['data']['annual_income']==160000.0
    details=client.get('/citizen/profile/details',headers=auth_headers)
    dashboard=client.get('/citizen/dashboard',headers=auth_headers)
    assert details.status_code==200
    assert dashboard.status_code==200
    assert details.json()['data']['extended_profile']['annual_income']==160000.0
    assert dashboard.json()['data']['extended_profile']['annual_income']==160000.0

def test_confirm_persists_extracted_fields_and_dashboard_reads_them(client: TestClient,auth_headers:dict):
    content=pdf_bytes('Name: Profile Citizen\nAnnual Income: 85000\nCaste: BC\nCommunity: MBC')
    uploaded=client.post('/api/documents/income_certificate/upload',headers=auth_headers,files={'file':('income.pdf',content,'application/pdf')})
    assert uploaded.status_code==201
    assert client.post('/api/documents/process-all',headers=auth_headers).status_code==200
    preview=client.get('/api/profile/preview',headers=auth_headers)
    fields=preview.json()['data']['fields']
    assert len(fields)>0
    assert fields['annual_income']=='85000'

    confirmed=client.post('/api/profile/confirm',headers=auth_headers)
    assert confirmed.status_code==200

    documents=client.get('/api/documents',headers=auth_headers)
    assert documents.status_code==200
    assert documents.json()['data']['items'][0]['upload_status']=='verified'
    temporary_preview=client.get('/api/profile/preview',headers=auth_headers)
    assert temporary_preview.status_code==200
    assert temporary_preview.json()['data']['fields']=={}

    details=client.get('/citizen/profile/details',headers=auth_headers)
    dashboard=client.get('/citizen/dashboard',headers=auth_headers)
    assert details.status_code==200
    assert dashboard.status_code==200
    assert details.json()['data']['extended_profile']['annual_income']==85000.0
    assert dashboard.json()['data']['extended_profile']['annual_income']==85000.0

def test_profile_conflict_requires_correction_before_confirmation(client: TestClient,auth_headers:dict):
    income=pdf_bytes('Name: Kumar\nAnnual Income: 150000')
    ration=pdf_bytes('Name: Other Kumar\nAddress: Test village')
    assert client.post('/api/documents/income_certificate/upload',headers=auth_headers,files={'file':('income.pdf',income,'application/pdf')}).status_code==201
    assert client.post('/api/documents/smart_ration_card/upload',headers=auth_headers,files={'file':('ration.pdf',ration,'application/pdf')}).status_code==201
    assert client.post('/api/documents/process-all',headers=auth_headers).status_code==200
    preview=client.get('/api/profile/preview',headers=auth_headers)
    assert any(item['field_name']=='full_name' for item in preview.json()['data']['conflicts'])
    assert preview.json()['data']['needs_review']==1
    assert client.post('/api/profile/confirm',headers=auth_headers).status_code==409
    assert client.post('/api/profile/correct',headers=auth_headers,json={'field_name':'full_name','value':'Kumar'}).status_code==200
    assert client.post('/api/profile/confirm',headers=auth_headers).status_code==200

def test_confirmation_skips_duplicate_ration_card_but_saves_profile(client: TestClient,auth_headers:dict):
    duplicate=pdf_bytes('Name: Existing Citizen\nCard Number: TEST-RATION-001')
    first=client.post('/api/documents/smart_ration_card/upload',headers=auth_headers,files={'file':('ration.pdf',duplicate,'application/pdf')})
    assert first.status_code==201
    assert client.post('/api/documents/process-all',headers=auth_headers).status_code==200
    assert client.post('/api/profile/confirm',headers=auth_headers).status_code==200

    second_registration=client.post('/auth/register',json={
        'email':'second@example.com','phone':'9876543212','full_name':'Second Citizen',
        'password':'TestPass123!','confirm_password':'TestPass123!',
        'district':'Chennai','state':'Tamil Nadu',
    })
    second_headers={'Authorization':f"Bearer {second_registration.json()['data']['access_token']}"}
    uploaded=client.post('/api/documents/smart_ration_card/upload',headers=second_headers,files={'file':('ration.pdf',duplicate,'application/pdf')})
    assert uploaded.status_code==201
    assert client.post('/api/documents/process-all',headers=second_headers).status_code==200
    assert client.post('/api/profile/confirm',headers=second_headers).status_code==200
