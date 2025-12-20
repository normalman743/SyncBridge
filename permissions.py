"""Compatibility shim for legacy permissions import path."""

from app.services.permissions import (
    assert_can_access_block,
    assert_can_add_function_to_form,
    assert_can_create_mainform,
    assert_can_create_subform,
    assert_can_delete_form,
    assert_can_edit_function,
    assert_can_edit_message,
    assert_can_post_message,
    assert_can_update_mainform,
    assert_can_update_subform,
    assert_can_upload_file,
    get_current_user,
    require_role,
    validate_status_transition,
)

__all__ = [
    "assert_can_access_block",
    "assert_can_add_function_to_form",
    "assert_can_create_mainform",
    "assert_can_create_subform",
    "assert_can_delete_form",
    "assert_can_edit_function",
    "assert_can_edit_message",
    "assert_can_post_message",
    "assert_can_update_mainform",
    "assert_can_update_subform",
    "assert_can_upload_file",
    "get_current_user",
    "require_role",
    "validate_status_transition",
]
