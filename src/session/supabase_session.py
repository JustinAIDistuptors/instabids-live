# src/session/supabase_session.py
print(f"[{__file__}] Attempting to load src.session.supabase_session", flush=True)
from google.adk.sessions import BaseSessionService, State
from supabase import create_client, Client as SupabaseClient
import os
import json
from typing import Dict, Any, Optional

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

class SupabaseSessionService(BaseSessionService):
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            print(f"[{__name__}] ERROR: Supabase URL or Service Role Key not configured for SessionService.")
            self.supabase_client = None
            # Consider raising an ImportError or a custom configuration error.
            # For now, operations will fail if the client is None.
        else:
            self.supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print(f"[{__name__}] SupabaseSessionService initialized. Client: {'OK' if self.supabase_client else 'Not Configured'}")

    async def async_get_session_state(self, session_id: str) -> Optional[State]:
        if not self.supabase_client:
            print(f"[{__name__}] Supabase client not initialized in SessionService. Cannot get state for session: {session_id}")
            # According to SessionService ABC, should probably raise an error or return None if unrecoverable.
            return None 

        print(f"[{__name__}] Attempting to get session state for session_id: {session_id}")
        try:
            response = await self.supabase_client.table("adk_sessions").select("state_data").eq("session_id", session_id).maybe_single().execute()
            if response.data and response.data.get("state_data") is not None:
                state_data_from_db = response.data["state_data"]
                # state_data could be a dict if Supabase auto-parses JSONB, or string if TEXT
                state_dict = {}
                if isinstance(state_data_from_db, str):
                    try:
                        state_dict = json.loads(state_data_from_db)
                    except json.JSONDecodeError:
                        print(f"[{__name__}] Error decoding JSON state_data for {session_id}: {state_data_from_db}")
                        return None # Or handle corrupted state
                elif isinstance(state_data_from_db, dict):
                    state_dict = state_data_from_db
                else:
                    print(f"[{__name__}] Unexpected type for state_data for {session_id}: {type(state_data_from_db)}")
                    return None

                print(f"[{__name__}] Session state found and parsed for {session_id}")
                return State(session_id=session_id, items=state_dict)
            elif response.error:
                print(f"[{__name__}] Supabase error getting session state for {session_id}: {response.error.message}")
                return None
            else: # No data and no error means session not found
                print(f"[{__name__}] No session state found for session_id: {session_id}.")
                return None
        except Exception as e:
            print(f"[{__name__}] Exception getting session state for {session_id}: {e}")
            return None

    async def async_set_session_state(self, session_id: str, state: State) -> None:
        if not self.supabase_client:
            print(f"[{__name__}] Supabase client not initialized in SessionService. Cannot set state for session: {session_id}")
            # Consider raising an error as this is a critical failure.
            return

        state_data_json = json.dumps(state.items)
        print(f"[{__name__}] Attempting to set session state for session_id: {session_id} with data items: {state.items}")
        try:
            response = await self.supabase_client.table("adk_sessions").upsert({
                "session_id": session_id,
                "state_data": state.items # Store as JSONB directly if column type is JSONB
            }).execute()
            
            if response.data:
                 print(f"[{__name__}] Successfully set session state for {session_id}")
            elif response.error:
                 print(f"[{__name__}] Supabase error setting session state for {session_id}: {response.error.message}")
                 # Consider raising an error
            else:
                 print(f"[{__name__}] Failed to set session state for {session_id} (no data/error): {response}")
                 # Consider raising an error

        except Exception as e:
            print(f"[{__name__}] Exception setting session state for {session_id}: {e}")
            # Consider raising an error

    async def async_delete_session_state(self, session_id: str) -> None:
        if not self.supabase_client:
            print(f"[{__name__}] Supabase client not initialized in SessionService. Cannot delete state for session: {session_id}")
            return

        print(f"[{__name__}] Attempting to delete session state for session_id: {session_id}")
        try:
            response = await self.supabase_client.table("adk_sessions").delete().eq("session_id", session_id).execute()
            if response.error:
                print(f"[{__name__}] Supabase error deleting session state for {session_id}: {response.error.message}")
            else:
                print(f"[{__name__}] Session state for {session_id} deleted (if existed).")
        except Exception as e:
            print(f"[{__name__}] Exception deleting session state for {session_id}: {e}")

    # Required synchronous methods by BaseSessionService
    def create_session(self, user_id: str, session = None) -> State: # type: ignore
        # TODO: Implement synchronous session creation or bridge to async
        print(f"[{__name__}] Synchronous create_session called but not implemented.")
        raise NotImplementedError("Synchronous create_session is not implemented.")

    def get_session(self, session_id: str) -> Optional[State]:
        # TODO: Implement synchronous session retrieval or bridge to async
        print(f"[{__name__}] Synchronous get_session called but not implemented.")
        raise NotImplementedError("Synchronous get_session is not implemented.")

    def list_sessions(self, user_id: str) -> list[State]: # type: ignore
        # TODO: Implement synchronous session listing or bridge to async
        print(f"[{__name__}] Synchronous list_sessions called but not implemented.")
        raise NotImplementedError("Synchronous list_sessions is not implemented.")

    def delete_session(self, session_id: str) -> None:
        # TODO: Implement synchronous session deletion or bridge to async
        print(f"[{__name__}] Synchronous delete_session called but not implemented.")
        raise NotImplementedError("Synchronous delete_session is not implemented.")

# Note: The 'adk_sessions' table needs to exist in Supabase with at least:
# - session_id (text, primary key)
# - state_data (jsonb is recommended)
# - last_updated_at (timestamptz, optional, defaults to now())
