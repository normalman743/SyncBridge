"""Compatibility shim that re-exports repository helpers."""

from app.repositories import blocks, files, forms, functions, licenses, messages, nonfunctions, users

get_user_by_email = users.get_by_email
get_user_by_id = users.get_by_id
create_user = users.create
authenticate = users.authenticate

get_license = licenses.get_by_key
activate_license = licenses.activate

get_form = forms.get
list_forms_for_user = forms.list_for_user
create_mainform = forms.create_mainform
update_form = forms.update_form
delete_form = forms.delete_form
create_subform = forms.create_subform

get_functions_by_form = functions.list_by_form
create_function = functions.create
update_function = functions.update
delete_function = functions.delete

get_nonfunctions_by_form = nonfunctions.list_by_form
create_nonfunction = nonfunctions.create
update_nonfunction = nonfunctions.update
delete_nonfunction = nonfunctions.delete

get_or_create_block = blocks.get_or_create

list_messages = messages.list_messages
create_message = messages.create_message
update_message = messages.update_message
delete_message = messages.delete_message

create_file_record = files.create_record
create_file = files.create_record
delete_file = files.delete_record

__all__ = [
    "get_user_by_email",
    "get_user_by_id",
    "create_user",
    "authenticate",
    "get_license",
    "activate_license",
    "get_form",
    "list_forms_for_user",
    "create_mainform",
    "update_form",
    "delete_form",
    "create_subform",
    "get_functions_by_form",
    "create_function",
    "update_function",
    "delete_function",
    "get_nonfunctions_by_form",
    "create_nonfunction",
    "update_nonfunction",
    "delete_nonfunction",
    "get_or_create_block",
    "list_messages",
    "create_message",
    "update_message",
    "delete_message",
    "create_file_record",
    "create_file",
    "delete_file",
]
