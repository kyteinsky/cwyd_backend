#
# SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
#
from ..dyn_loader import VectorDBLoader
from .base import BaseVectorDB
from .types import DbException, UpdateAccessOp


# todo: return source ids that were successfully deleted
def delete_by_source(vectordb_loader: VectorDBLoader, source_ids: list[str]):
	db: BaseVectorDB = vectordb_loader.load()
	try:
		db.delete_source_ids(source_ids)
	except Exception as e:
		raise DbException('Error: Vectordb delete_source_ids error') from e


def delete_by_provider(vectordb_loader: VectorDBLoader, provider_key: str):
	db: BaseVectorDB = vectordb_loader.load()
	db.delete_provider(provider_key)


def delete_user(vectordb_loader: VectorDBLoader, user_id: str):
	db: BaseVectorDB = vectordb_loader.load()
	db.delete_user(user_id)


def update_access(
	vectordb_loader: VectorDBLoader,
	op: UpdateAccessOp,
	user_ids: list[str],
	source_id: str,
):
	db: BaseVectorDB = vectordb_loader.load()
	db.update_access(op, user_ids, source_id)


def update_access_provider(
	vectordb_loader: VectorDBLoader,
	op: UpdateAccessOp,
	user_ids: list[str],
	provider_id: str,
):
	db: BaseVectorDB = vectordb_loader.load()
	db.update_access_provider(op, user_ids, provider_id)


def decl_update_access(
	vectordb_loader: VectorDBLoader,
	user_ids: list[str],
	source_id: str,
):
	db: BaseVectorDB = vectordb_loader.load()
	db.decl_update_access(user_ids, source_id)
