"""JWT-protected citizen document intelligence APIs."""
from fastapi import APIRouter,Depends,File,HTTPException,UploadFile
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.schemas.citizen import SuccessResponse
from app.schemas.citizen_document import DocumentProcessRequest,ProfileVerifyRequest,ProfileCorrectionRequest
from app.services.document_intelligence_service import DocumentIntelligenceService
from app.models.citizen_document import CitizenDocumentType, ProfileConflict
router=APIRouter(prefix='/api',tags=['Citizen Document Intelligence'])
def dump(x):return {c.name:(getattr(x,c.name).value if hasattr(getattr(x,c.name),'value') else getattr(x,c.name)) for c in x.__table__.columns}
def service(db):return DocumentIntelligenceService(db)
@router.post('/documents/{document_type}/upload',response_model=SuccessResponse,status_code=201)
async def upload(document_type:CitizenDocumentType,file:UploadFile=File(...),user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    try:return SuccessResponse(success=True,message='Document uploaded successfully',data=dump(service(db).upload(user,file,document_type)))
    except ValueError as e:raise HTTPException(422,{'error':'INVALID_DOCUMENT','message':str(e)})
@router.post('/documents/process',response_model=SuccessResponse)
async def process(payload:DocumentProcessRequest,user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    try:return SuccessResponse(success=True,message='Document processed successfully',data={'extracted_fields':service(db).process(user,payload.document_id)})
    except ValueError as e:raise HTTPException(404,{'error':'DOCUMENT_NOT_FOUND','message':str(e)})
@router.get('/documents',response_model=SuccessResponse)
async def documents(user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    return SuccessResponse(success=True,message='Documents retrieved successfully',data={'items':[dump(x) for x in service(db).documents(user)]})
@router.post('/documents/process-all',response_model=SuccessResponse)
async def process_all(user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    return SuccessResponse(success=True,message='Documents processed successfully',data={'results':service(db).process_all(user)})
@router.get('/documents/status/{document_id}',response_model=SuccessResponse)
async def status(document_id:str,user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    try:return SuccessResponse(success=True,message='Document status retrieved successfully',data=dump(service(db)._owned(user,document_id)))
    except ValueError as e:raise HTTPException(404,{'error':'DOCUMENT_NOT_FOUND','message':str(e)})
@router.get('/documents/extracted/{document_id}',response_model=SuccessResponse)
async def extracted(document_id:str,user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    try:return SuccessResponse(success=True,message='Extracted information retrieved successfully',data={'items':[dump(x) for x in service(db).extracted(user,document_id)]})
    except ValueError as e:raise HTTPException(404,{'error':'DOCUMENT_NOT_FOUND','message':str(e)})
@router.post('/profile/generate',response_model=SuccessResponse)
async def generate(user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    profile,fields=service(db).generate_profile(user);return SuccessResponse(success=True,message='Digital profile generated successfully',data={'profile':dump(profile),'source_fields':fields})
@router.post('/profile/verify',response_model=SuccessResponse)
async def verify(payload:ProfileVerifyRequest,user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    try:return SuccessResponse(success=True,message='Extracted information verified successfully',data=dump(service(db).verify(user,payload.document_id,payload.approved_fields)))
    except ValueError as e:raise HTTPException(404,{'error':'DOCUMENT_NOT_FOUND','message':str(e)})
@router.get('/profile/completeness',response_model=SuccessResponse)
async def completeness(user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    return SuccessResponse(success=True,message='Profile completeness retrieved successfully',data=service(db).completeness(user))
@router.get('/profile/preview',response_model=SuccessResponse)
async def preview(user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    fields,conflicts=service(db).preview(user)
    return SuccessResponse(success=True,message='Profile preview generated successfully',data={'fields':fields,'conflicts':[dump(x) for x in conflicts],'verified_fields':0,'needs_review':len(fields)})
@router.get('/profile/conflicts',response_model=SuccessResponse)
async def conflicts(user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    items=db.query(ProfileConflict).filter_by(citizen_id=user,is_resolved=False).all()
    return SuccessResponse(success=True,message='Profile conflicts retrieved successfully',data={'items':[dump(x) for x in items]})
@router.post('/profile/correct',response_model=SuccessResponse)
async def correct(payload:ProfileCorrectionRequest,user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    try:return SuccessResponse(success=True,message='Profile field corrected successfully',data=dump(service(db).correct(user,payload.field_name,payload.value)))
    except ValueError as e:raise HTTPException(404,{'error':'FIELD_NOT_FOUND','message':str(e)})
@router.post('/profile/confirm',response_model=SuccessResponse)
async def confirm(user:str=Depends(get_current_user),db:Session=Depends(get_db)):
    try:return SuccessResponse(success=True,message='Citizen profile confirmed successfully',data=dump(service(db).confirm(user)))
    except ValueError as e:raise HTTPException(409,{'error':'PROFILE_REVIEW_REQUIRED','message':str(e)})
