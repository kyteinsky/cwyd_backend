from os import getenv
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Body, FastAPI, Request, UploadFile, BackgroundTasks
from langchain.llms.base import LLM

from .chain import embed_sources, process_query
from .download import download_all_models
from .ocs_utils import AppAPIAuthMiddleware
from .utils import enabled_guard, JSONResponse, update_progress, value_of
from .vectordb import BaseVectorDB

load_dotenv()

app = FastAPI(debug=getenv('DEBUG', '0') == '1')


# middlewares

if value_of(getenv('DISABLE_AAA', '0')) == '0':
	app.add_middleware(AppAPIAuthMiddleware)


@app.get('/')
def _(request: Request):
	'''
	Server check
	'''
	return f'Hello, {request.scope.get("username", "anon")}!'


# TODO: for testing, remove later
@app.get('/world')
@enabled_guard(app)
def _(query: str | None = None):
	em = app.extra.get('EMBEDDING_MODEL')
	return em.embed_query(query if query is not None else 'what is an apple?')


# TODO: for testing, remove later
@app.get('/vectors')
@enabled_guard(app)
def _(userId: str):
	from chromadb import ClientAPI
	from .vectordb import COLLECTION_NAME

	db: BaseVectorDB = app.extra.get('VECTOR_DB')
	client: ClientAPI = db.client
	db.setup_schema(userId)

	return JSONResponse(
		client.get_collection(COLLECTION_NAME(userId)).get()
	)


# TODO: for testing, remove later
@app.get('/search')
@enabled_guard(app)
def _(userId: str, sourceNames: str):
	sourceNames: list[str] = [source.strip() for source in sourceNames.split(',') if source.strip() != '']

	if len(sourceNames) == 0:
		return JSONResponse('No sources provided', 400)

	db: BaseVectorDB = app.extra.get('VECTOR_DB')

	if db is None:
		return JSONResponse('Error: VectorDB not initialised', 500)

	source_objs = db.get_objects_from_metadata(userId, 'source', sourceNames)
	sources = list(map(lambda s: s.get('id'), source_objs.values()))

	return JSONResponse({ 'sources': sources })


@app.put('/enabled')
def _(enabled: bool):
	app.extra['ENABLED'] = enabled
	print('App', 'enabled' if enabled else 'disabled', flush=True)
	return JSONResponse(content={'error': ''}, status_code=200)


@app.get('/heartbeat')
def _():
	print('heartbeat_handler: result=ok')
	return JSONResponse(content={'status': 'ok'}, status_code=200)


@app.post('/init')
def _(bg_tasks: BackgroundTasks):
	if not app.extra.get('ENABLED', False):
		bg_tasks.add_task(download_all_models, app)
		return JSONResponse(content={}, status_code=200)

	update_progress(100)
	print('App already initialised', flush=True)
	return JSONResponse(content={}, status_code=200)


@app.post('/deleteSources')
@enabled_guard(app)
def _(userId: Annotated[str, Body()], sourceNames: Annotated[list[str], Body()]):
	sourceNames = [source.strip() for source in sourceNames if source.strip() != '']

	if len(sourceNames) == 0:
		return JSONResponse('No sources provided', 400)

	db: BaseVectorDB = app.extra.get('VECTOR_DB')

	if db is None:
		return JSONResponse('Error: VectorDB not initialised', 500)

	res = db.delete(userId, 'source', sourceNames)

	if res is False:
		return JSONResponse('Error: VectorDB delete failed, check vectordb logs for more info.', 400)

	return JSONResponse('All valid sources deleted')


@app.post('/deleteSourcesByProvider')
@enabled_guard(app)
def _(userId: Annotated[str, Body()], providerKey: Annotated[str, Body()]):
	if value_of(providerKey) is None:
		return JSONResponse('Invalid provider key provided', 400)

	db: BaseVectorDB = app.extra.get('VECTOR_DB')

	if db is None:
		return JSONResponse('Error: VectorDB not initialised', 500)

	res = db.delete(userId, 'provider', [providerKey])

	if res is False:
		return JSONResponse('Error: VectorDB delete failed, check vectordb logs for more info.', 400)

	return JSONResponse('All valid sources deleted')


@app.put('/loadSources')
@enabled_guard(app)
def _(sources: list[UploadFile]):
	if len(sources) == 0:
		return JSONResponse('No sources provided', 400)

	# TODO: headers validation using pydantic
	if not all([
		value_of(source.headers.get('userId'))
		and value_of(source.headers.get('type'))
		and value_of(source.headers.get('modified'))
		and value_of(source.headers.get('provider'))
		for source in sources]
	):
		return JSONResponse('Invaild/missing headers', 400)

	db: BaseVectorDB = app.extra.get('VECTOR_DB')
	if db is None:
		return JSONResponse('Error: VectorDB not initialised', 500)

	result = embed_sources(db, sources)
	if not result:
		return JSONResponse('Error: All sources were not loaded, check logs for more info', 500)

	return JSONResponse('All sources loaded')


@app.get('/query')
@enabled_guard(app)
def _(userId: str, query: str, useContext: bool = True, ctxLimit: int = 5):
	llm: LLM = app.extra.get('LLM_MODEL')
	if llm is None:
		return JSONResponse('Error: LLM not initialised', 500)

	db: BaseVectorDB = app.extra.get('VECTOR_DB')
	if db is None:
		return JSONResponse('Error: VectorDB not initialised', 500)

	template = app.extra.get('LLM_TEMPLATE')
	end_separator = app.extra.get('LLM_END_SEPARATOR', '')

	(output, sources) = process_query(
		user_id=userId,
		vectordb=db,
		llm=llm,
		query=query,
		use_context=useContext,
		ctx_limit=ctxLimit,
		end_separator=end_separator,
		**({'template': template} if template else {}),
	)

	if output is None:
		return JSONResponse('Error: check if the model specified supports the query type', 500)

	return JSONResponse({
		'output': output,
		'sources': sources,
	})
