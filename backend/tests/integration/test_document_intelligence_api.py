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
    assert client.post('/api/profile/correct',headers=auth_headers,json={'field_name':'annual_income','value':'160000'}).status_code==200
    confirmed=client.post('/api/profile/confirm',headers=auth_headers)
    assert confirmed.status_code==200
    assert confirmed.json()['data']['annual_income']==160000.0

def test_profile_conflict_requires_correction_before_confirmation(client: TestClient,auth_headers:dict):
    income=pdf_bytes('Name: Kumar\nAnnual Income: 150000')
    ration=pdf_bytes('Name: Other Kumar\nAddress: Test village')
    assert client.post('/api/documents/income_certificate/upload',headers=auth_headers,files={'file':('income.pdf',income,'application/pdf')}).status_code==201
    assert client.post('/api/documents/smart_ration_card/upload',headers=auth_headers,files={'file':('ration.pdf',ration,'application/pdf')}).status_code==201
    assert client.post('/api/documents/process-all',headers=auth_headers).status_code==200
    preview=client.get('/api/profile/preview',headers=auth_headers)
    assert any(item['field_name']=='full_name' for item in preview.json()['data']['conflicts'])
    assert client.post('/api/profile/confirm',headers=auth_headers).status_code==409
    assert client.post('/api/profile/correct',headers=auth_headers,json={'field_name':'full_name','value':'Kumar'}).status_code==200
    assert client.post('/api/profile/confirm',headers=auth_headers).status_code==200
