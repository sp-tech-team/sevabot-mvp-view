# user_management.py - User management with email whitelist
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from constants import USER_ROLES
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from supabase import create_client
import time

class UserManagement:
    """User and email whitelist management"""
    
    def __init__(self):
        self.supabase = None
        self._init_connection()
    
    def _init_connection(self):
        """Initialize Supabase connection"""
        try:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        except Exception as e:
            print(f"Error initializing Supabase connection: {e}")
    
    def _ensure_connection(self):
        """Ensure connection is alive, recreate if needed"""
        if not self.supabase:
            self._init_connection()
    
    def _retry_operation(self, operation, max_retries=3):
        """Retry operation on connection failure"""
        for attempt in range(max_retries):
            try:
                self._ensure_connection()
                return operation()
            except Exception as e:
                error_str = str(e)
                if "10054" in error_str or "connection" in error_str.lower():
                    print(f"Connection error (attempt {attempt+1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                        self._init_connection()  # Recreate connection
                        continue
                raise
    
    # ========== EMAIL WHITELIST MANAGEMENT ==========
    
    def validate_sadhguru_domain(self, email: str) -> tuple:
        """Validate if email belongs to sadhguru.org domain"""
        if not email or "@" not in email:
            return False, "Invalid email format"
        
        email_lower = email.lower().strip()
        
        if not email_lower.endswith("@sadhguru.org"):
            return False, "Only @sadhguru.org emails are allowed"
        
        return True, "Valid domain"
    
    def get_whitelisted_emails(self) -> List[Dict]:
        """Get all whitelisted emails"""
        def _get():
            result = self.supabase.table("email_whitelist")\
                .select("*")\
                .eq("is_active", True)\
                .order("added_at", desc=True)\
                .execute()
            return result.data if result.data else []
        
        try:
            return self._retry_operation(_get)
        except Exception as e:
            print(f"Error getting whitelisted emails: {e}")
            return []
    
    def add_email_to_whitelist(self, email: str, added_by: str, department: str = None) -> tuple:
        """Add email to whitelist with department"""
        try:
            email_lower = email.lower().strip()
            
            # Validate domain first
            is_valid, domain_message = self.validate_sadhguru_domain(email_lower)
            if not is_valid:
                return False, domain_message
            
            # Check if email already exists (active or inactive)
            existing = self.supabase.table("email_whitelist")\
                .select("*")\
                .eq("email", email_lower)\
                .execute()
            
            if existing.data:
                # Email exists - check if it's inactive
                if not existing.data[0].get('is_active', True):
                    # Reactivate it
                    update_data = {"is_active": True, "added_by": added_by}
                    if department:
                        update_data["department"] = department
                    
                    result = self.supabase.table("email_whitelist")\
                        .update(update_data)\
                        .eq("email", email_lower)\
                        .execute()
                    print(f"✅ Reactivated {email_lower}")
                    return bool(result.data), f"Successfully reactivated {email_lower}"
                else:
                    # Already active
                    print(f"⚠️ Email {email_lower} already in whitelist")
                    return False, f"Email {email_lower} is already in the whitelist"
            
            # New email - insert it
            email_data = {
                "email": email_lower,
                "added_by": added_by,
                "is_active": True
            }
            
            if department:
                email_data["department"] = department
            
            result = self.supabase.table("email_whitelist")\
                .insert(email_data)\
                .execute()
            
            print(f"✅ Added {email_lower} to whitelist")
            return bool(result.data), f"Successfully added {email_lower} to whitelist"
        except Exception as e:
            error_msg = f"Error adding email to whitelist: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def remove_email_from_whitelist(self, email: str) -> bool:
        """Remove email from whitelist - actually delete the record"""
        try:
            result = self.supabase.table("email_whitelist")\
                .delete()\
                .eq("email", email.lower())\
                .execute()
            
            return True
        except Exception as e:
            print(f"Error removing email from whitelist: {e}")
            return False
    
    def is_email_whitelisted(self, email: str) -> bool:
        """Check if email is whitelisted"""
        try:
            result = self.supabase.table("email_whitelist")\
                .select("id")\
                .eq("email", email.lower())\
                .eq("is_active", True)\
                .execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error checking email whitelist: {e}")
            return False
    
    # ========== USER MANAGEMENT ==========
    
    def get_all_users(self) -> List[Dict]:
        """Get all users from email_whitelist (whether logged in or not)"""
        def _get():
            # Get from whitelist with roles
            whitelist_result = self.supabase.table("email_whitelist")\
                .select("email, role, department, added_at, added_by")\
                .eq("is_active", True)\
                .order("added_at", desc=True)\
                .execute()
            
            if not whitelist_result.data:
                return []
            
            # Get user details for name and last_login
            users_result = self.supabase.table("users")\
                .select("email, name, last_login, created_at")\
                .execute()
            
            users_map = {u['email']: u for u in users_result.data} if users_result.data else {}
            
            # Merge data
            result = []
            for w in whitelist_result.data:
                email = w['email']
                user_data = users_map.get(email, {})
                
                result.append({
                    'email': email,
                    'name': user_data.get('name') or email.split('@')[0].replace('.', ' ').replace('-', ' ').title(),
                    'role': w.get('role', 'user'),
                    'last_login': user_data.get('last_login'),
                    'created_at': w.get('added_at') or user_data.get('created_at'),
                    'department': w.get('department') or "",  # Empty string instead of None
                    'added_by': w.get('added_by')
                })
            
            return result
        
        try:
            return self._retry_operation(_get)
        except Exception as e:
            print(f"Error getting users: {e}")
            return []
    
    def get_users_by_role(self, role: str) -> List[List[str]]:
        """Get users formatted for table display by role - always fresh data"""
        try:
            users = self.get_all_users()  # Always get fresh data
            filtered_users = [user for user in users if user['role'] == role]
            
            # Format for table: [Name, Email, Last Login, Date Added]
            table_data = []
            for user in filtered_users:
                table_data.append([
                    user.get('name', 'Unknown'),
                    user['email'],
                    user.get('last_login', 'Never')[:10] if user.get('last_login') else 'Never',
                    user.get('created_at', 'Unknown')[:10] if user.get('created_at') else 'Unknown'
                ])
            
            return table_data
        except Exception as e:
            print(f"Error getting users by role: {e}")
            return []
    
    def get_users_by_role_simple(self, role: str) -> List[Dict]:
        """Get users by role as simple dict list for dropdown population"""
        try:
            users = self.get_all_users()
            if role.lower() == 'all':
                return users
            else:
                return [user for user in users if user['role'] == role]
        except Exception as e:
            print(f"Error getting users by role simple: {e}")
            return []
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get a single user by email"""
        try:
            result = self.supabase.table("email_whitelist")\
                .select("*")\
                .eq("email", email.lower())\
                .eq("is_active", True)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None
    
    def format_user_for_dropdown(self, user: Dict) -> str:
        """Format user for dropdown display - prevents nested names"""
        email = user['email']
        # Extract clean name from email if name is already formatted with email
        name = user.get('name', '')
        
        # Check if name already contains the email (to prevent nesting)
        if email in name or '(' in name:
            # Name already formatted or contains email, just use email
            name = email.split('@')[0].replace('.', ' ').replace('-', ' ').title()
        
        return f"{name} ({email})"
    
    def get_dropdown_choices_by_role(self, role: str) -> List[Tuple[str, str]]:
        """Get dropdown choices (label, value) for a specific role"""
        users = self.get_users_by_role_simple(role)
        return [(self.format_user_for_dropdown(u), u['email']) for u in users]
    
    def promote_user_to_spoc(self, user_email: str) -> bool:
        """Promote a user to SPOC role in whitelist"""
        try:
            print(f"DEBUG promote_user_to_spoc: Starting for {user_email}")
            
            # Update role in whitelist (single source of truth)
            result = self.supabase.table("email_whitelist")\
                .update({"role": "spoc"})\
                .eq("email", user_email.lower())\
                .execute()
            
            print(f"DEBUG promote_user_to_spoc: Whitelist update result: {result.data}")
            
            # Also update in users table if they've logged in
            try:
                self.supabase.table("users")\
                    .update({"role": "spoc"})\
                    .eq("email", user_email.lower())\
                    .execute()
            except:
                pass  # User hasn't logged in yet, that's fine
            
            return bool(result.data)
        except Exception as e:
            print(f"ERROR promote_user_to_spoc: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def demote_spoc_to_user(self, spoc_email: str, reassign_to_spoc: str = None) -> bool:
        """Demote a SPOC back to regular user in whitelist"""
        try:
            # Get assigned users
            assigned_users = self.get_spoc_assignments(spoc_email)
            
            # If there are assigned users and a reassignment SPOC is provided
            if assigned_users and reassign_to_spoc:
                # Reassign all users to the new SPOC
                for user_email in assigned_users:
                    self.add_spoc_assignment(reassign_to_spoc, user_email)
            
            # Remove all old SPOC assignments
            self.supabase.table("spoc_assignments")\
                .delete()\
                .eq("spoc_email", spoc_email.lower())\
                .execute()
            
            # Update role to user in whitelist
            result = self.supabase.table("email_whitelist")\
                .update({"role": "user"})\
                .eq("email", spoc_email.lower())\
                .execute()
            
            # Also update in users table if they've logged in
            try:
                self.supabase.table("users")\
                    .update({"role": "user"})\
                    .eq("email", spoc_email.lower())\
                    .execute()
            except:
                pass
            
            return bool(result.data)
        except Exception as e:
            print(f"Error demoting SPOC to user: {e}")
            return False
    
    def promote_spoc_to_admin(self, spoc_email: str) -> bool:
        """Promote a SPOC to Admin role in whitelist"""
        try:
            # Update role in whitelist
            result = self.supabase.table("email_whitelist")\
                .update({"role": "admin"})\
                .eq("email", spoc_email.lower())\
                .execute()
            
            # Also update in users table if they've logged in
            try:
                self.supabase.table("users")\
                    .update({"role": "admin"})\
                    .eq("email", spoc_email.lower())\
                    .execute()
            except:
                pass
            
            return bool(result.data)
        except Exception as e:
            print(f"Error promoting SPOC to Admin: {e}")
            return False
    
    def demote_admin_to_spoc(self, admin_email: str) -> bool:
        """Demote an Admin to SPOC role in whitelist"""
        try:
            # Update role in whitelist
            result = self.supabase.table("email_whitelist")\
                .update({"role": "spoc"})\
                .eq("email", admin_email.lower())\
                .execute()
            
            # Also update in users table if they've logged in
            try:
                self.supabase.table("users")\
                    .update({"role": "spoc"})\
                    .eq("email", admin_email.lower())\
                    .execute()
            except:
                pass
            
            return bool(result.data)
        except Exception as e:
            print(f"Error demoting Admin to SPOC: {e}")
            return False
    
    def demote_admin_to_user(self, admin_email: str) -> bool:
        """Demote an Admin to regular user role in whitelist"""
        try:
            # Update role in whitelist
            result = self.supabase.table("email_whitelist")\
                .update({"role": "user"})\
                .eq("email", admin_email.lower())\
                .execute()
            
            # Also update in users table if they've logged in
            try:
                self.supabase.table("users")\
                    .update({"role": "user"})\
                    .eq("email", admin_email.lower())\
                    .execute()
            except:
                pass
            
            return bool(result.data)
        except Exception as e:
            print(f"Error demoting Admin to user: {e}")
            return False
    
    def get_users_with_details(self, role_filter: str = "All") -> List[List[str]]:
        """Get users with full details for hierarchy table"""
        try:
            users = self.get_all_users()
            
            # Filter by role
            if role_filter != "All":
                users = [u for u in users if u['role'] == role_filter.lower()]
            
            # Format for table: [Name, Email, Role, Added By, Last Login, Date Added]
            table_data = []
            for user in users:
                table_data.append([
                    user.get('name', 'Unknown'),
                    user['email'],
                    user['role'].upper(),
                    'system',  # Can be enhanced if we track who added them
                    user.get('last_login', 'Never')[:19] if user.get('last_login') else 'Never',
                    user.get('created_at', 'Unknown')[:10] if user.get('created_at') else 'Unknown'
                ])
            
            return table_data
        except Exception as e:
            print(f"Error getting users with details: {e}")
            return []
    
    def get_assignments_with_names(self, spoc_filter: str = "ALL") -> List[List[str]]:
        """Get assignments with clean name/email separation"""
        try:
            assignments_result = self.supabase.table("spoc_assignments")\
                .select("*")\
                .order("created_at", desc=True)\
                .execute()
            
            if not assignments_result.data:
                return []
            
            # Get user details
            users = self.get_all_users()
            user_details = {user['email']: user['name'] for user in users}
            
            # Build assignments table
            assignments_data = []
            for assignment in assignments_result.data:
                spoc_email = assignment["spoc_email"]
                user_email = assignment["assigned_user_email"]
                created_date = assignment["created_at"][:10]
                
                # Filter if needed
                if spoc_filter != "ALL" and spoc_email != spoc_filter:
                    continue
                
                # Get CLEAN names - if user hasn't logged in, extract from email
                if spoc_email in user_details:
                    spoc_name = user_details[spoc_email]
                else:
                    spoc_name = spoc_email.split('@')[0].replace('.', ' ').title()
                
                if user_email in user_details:
                    user_name = user_details[user_email]
                else:
                    user_name = user_email.split('@')[0].replace('.', ' ').title()
                
                # Table format: [SPOC Name (clean), SPOC Email, User Email, User Name (clean), Date]
                assignments_data.append([
                    spoc_name,      # Just name, no email
                    spoc_email,     # Just email
                    user_email,     # Just email
                    user_name,      # Just name, no email
                    created_date
                ])
            
            return assignments_data
        except Exception as e:
            print(f"Error loading assignments with names: {e}")
            return []

    
    # ========== SPOC ASSIGNMENTS ==========
    
    def add_spoc_assignment(self, spoc_email: str, user_email: str) -> bool:
        """Add user assignment to SPOC - user can only be assigned to ONE SPOC"""
        try:
            # Check if user is already assigned to ANY SPOC
            existing = self.supabase.table("spoc_assignments")\
                .select("spoc_email")\
                .eq("assigned_user_email", user_email)\
                .execute()
            
            if existing.data:
                current_spoc = existing.data[0]["spoc_email"]
                print(f"User {user_email} already assigned to {current_spoc}")
                # Remove old assignment first
                self.supabase.table("spoc_assignments")\
                    .delete()\
                    .eq("assigned_user_email", user_email)\
                    .execute()
                print(f"Removed old assignment, now assigning to {spoc_email}")
            
            # Add new assignment
            assignment_data = {
                "spoc_email": spoc_email,
                "assigned_user_email": user_email
            }
            
            result = self.supabase.table("spoc_assignments")\
                .insert(assignment_data)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error adding SPOC assignment: {e}")
            return False
    
    def remove_spoc_assignment(self, spoc_email: str, user_email: str) -> bool:
        """Remove user assignment from SPOC"""
        try:
            result = self.supabase.table("spoc_assignments")\
                .delete()\
                .eq("spoc_email", spoc_email)\
                .eq("assigned_user_email", user_email)\
                .execute()
            
            return True
        except Exception as e:
            print(f"Error removing SPOC assignment: {e}")
            return False
    
    def get_spoc_assignments(self, spoc_email: str) -> List[str]:
        """Get list of users assigned to a SPOC"""
        try:
            result = self.supabase.table("spoc_assignments")\
                .select("assigned_user_email")\
                .eq("spoc_email", spoc_email)\
                .execute()
            
            if result.data:
                return [item["assigned_user_email"] for item in result.data]
            return []
        except Exception as e:
            print(f"Error getting SPOC assignments: {e}")
            return []
    
    def get_all_spoc_assignments(self) -> Dict[str, List[str]]:
        """Get all SPOC assignments"""
        try:
            result = self.supabase.table("spoc_assignments")\
                .select("*")\
                .execute()
            
            assignments = {}
            if result.data:
                for item in result.data:
                    spoc_email = item["spoc_email"]
                    user_email = item["assigned_user_email"]
                    
                    if spoc_email not in assignments:
                        assignments[spoc_email] = []
                    assignments[spoc_email].append(user_email)
            
            return assignments
        except Exception as e:
            print(f"Error getting all SPOC assignments: {e}")
            return {}
    
    def get_assignments_overview_table(self) -> List[List[str]]:
        """Get assignments formatted for overview table"""
        try:
            assignments_result = self.supabase.table("spoc_assignments")\
                .select("*")\
                .order("created_at", desc=True)\
                .execute()
            
            if not assignments_result.data:
                return []
            
            # Get user details for names
            users = self.get_all_users()
            user_details = {user['email']: user['name'] for user in users}
            
            def get_name(email):
                """Get name from database or extract from email"""
                if email in user_details:
                    return user_details[email]
                # Extract name from email: first.last@domain → First Last
                name_part = email.split('@')[0]
                return ' '.join(word.capitalize() for word in name_part.replace('.', ' ').replace('-', ' ').split())
            
            # Build assignments table
            assignments_data = []
            for assignment in assignments_result.data:
                spoc_email = assignment["spoc_email"]
                user_email = assignment["assigned_user_email"]
                created_date = assignment["created_at"][:10]
                
                assignments_data.append([
                    get_name(spoc_email),  # SPOC Name
                    spoc_email,  # SPOC Email
                    user_email,  # User Email
                    get_name(user_email),  # User Name
                    created_date  # Date Added
                ])
            
            return assignments_data
        except Exception as e:
            print(f"Error loading assignments overview: {e}")
            return []
    
    def get_assignable_users_for_spoc(self) -> List[Dict]:
        """Get users that can be assigned to SPOCs (from whitelist, excluding already assigned)"""
        try:
            # Get all assignments to exclude already assigned users
            assigned_result = self.supabase.table("spoc_assignments")\
                .select("assigned_user_email").execute()
            assigned_emails = {item["assigned_user_email"] for item in assigned_result.data or []}
            
            # Get all whitelisted emails
            whitelist = self.get_whitelisted_emails()
            
            # Get already registered users for name mapping
            registered_users = self.get_all_users()
            user_names = {user['email']: user['name'] for user in registered_users}
            
            # Build assignable users list
            assignable_users = []
            for email_record in whitelist:
                email = email_record['email']
                # Skip admin emails and already assigned users
                if (email not in assigned_emails and 
                    email not in ['swapnil.padhi-ext@sadhguru.org', 'abhishek.kumar2019@sadhguru.org']):
                    
                    assignable_users.append({
                        'email': email,
                        'name': user_names.get(email, email.split('@')[0].replace('.', ' ').title()),
                        'is_registered': email in user_names
                    })
            
            return assignable_users
        except Exception as e:
            print(f"Error getting assignable users: {e}")
            return []

    def get_spoc_users(self) -> List[str]:
        """Get list of SPOC users for dropdown"""
        try:
            spoc_users = [user for user in self.get_all_users() if user['role'] == 'spoc']
            return [user['email'] for user in spoc_users]
        except Exception as e:
            print(f"Error getting SPOC users: {e}")
            return []
    
    # ========== DEPARTMENT MANAGEMENT ==========
    
    def get_departments(self) -> List[str]:
        """Get all departments from departments table"""
        def _get():
            result = self.supabase.table("departments")\
                .select("name")\
                .order("name")\
                .execute()
            return [item["name"] for item in result.data] if result.data else []
        
        try:
            return self._retry_operation(_get)
        except Exception as e:
            print(f"Error getting departments: {e}")
            return []
    
    def add_department(self, dept_name: str, added_by: str) -> tuple:
        """Add a new department to departments table"""
        try:
            dept_name = dept_name.strip()
            if not dept_name:
                return False, "Department name cannot be empty"
            
            # Check if already exists
            existing_depts = self.get_departments()
            if dept_name in existing_depts:
                return False, f"Department '{dept_name}' already exists"
            
            # Add to departments table
            result = self.supabase.table("departments")\
                .insert({"name": dept_name, "created_by": added_by})\
                .execute()
            
            return bool(result.data), f"Department '{dept_name}' added successfully"
        except Exception as e:
            return False, f"Error adding department: {str(e)}"
    
    def delete_department(self, dept_name: str) -> tuple:
        """Delete a department (only if no users assigned)"""
        try:
            # Check if any users have this department
            result = self.supabase.table("email_whitelist")\
                .select("email")\
                .eq("department", dept_name)\
                .eq("is_active", True)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return False, f"Cannot delete '{dept_name}' - {len(result.data)} user(s) assigned"
            
            # Delete from departments table
            self.supabase.table("departments")\
                .delete()\
                .eq("name", dept_name)\
                .execute()
            
            return True, f"Department '{dept_name}' deleted successfully"
        except Exception as e:
            return False, f"Error deleting department: {str(e)}"
    
    def get_whitelisted_emails_with_roles(self) -> List[Dict]:
        """Get whitelisted emails with their roles (now directly from whitelist)"""
        return self.get_whitelisted_emails()
    
    # ========== MISSING METHODS FOR UI ==========
    
    def update_user_role(self, email: str, new_role: str) -> bool:
        """Update a user's role in whitelist"""
        try:
            print(f'Updating user role for {email} to {new_role}')
            
            # Update role in whitelist (primary source)
            result = self.supabase.table("email_whitelist")\
                .update({"role": new_role})\
                .eq("email", email.lower())\
                .execute()
            
            print(f"Whitelist update result: {result.data}")
            
            # Also update in users table if they've logged in
            try:
                self.supabase.table("users")\
                    .update({"role": new_role})\
                    .eq("email", email.lower())\
                    .execute()
            except:
                pass
            
            # If demoting SPOC to user, handle their assignments
            if new_role == USER_ROLES['user']:
                # Remove all SPOC assignments where this person was the SPOC
                self.supabase.table("spoc_assignments")\
                    .delete()\
                    .eq("spoc_email", email.lower())\
                    .execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error updating user role: {e}")
            return False
    
    def update_user_department(self, email: str, department: str) -> bool:
        """Update user's department in whitelist"""
        try:
            result = self.supabase.table("email_whitelist")\
                .update({"department": department})\
                .eq("email", email.lower())\
                .execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error updating user department: {e}")
            return False
    
    def remove_all_spoc_assignments_for_user(self, user_email: str) -> bool:
        """Remove all SPOC assignments for a specific user"""
        try:
            self.supabase.table("spoc_assignments")\
                .delete()\
                .eq("assigned_user_email", user_email.lower())\
                .execute()
            return True
        except Exception as e:
            print(f"Error removing SPOC assignments: {e}")
            return False
    
    def get_whitelist_table(self) -> List[List[str]]:
        """Get whitelist data with Role column for table display"""
        try:
            whitelist = self.get_whitelisted_emails()
            
            table_data = []
            for item in whitelist:
                email = item['email']
                role = item.get('role', 'user')
                department = item.get('department') or ""  # Empty string instead of N/A
                added_by = item.get('added_by', 'N/A')
                added_at = item.get('added_at', '')
                
                # Format date
                if added_at:
                    try:
                        dt = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d')
                    except:
                        date_str = added_at[:10] if len(added_at) >= 10 else 'N/A'
                else:
                    date_str = 'N/A'
                
                # Format: [Email, Role, Department, Added By, Date Added]
                table_data.append([email, role.upper(), department, added_by, date_str])
            
            return table_data
        except Exception as e:
            print(f"Error getting whitelist table: {e}")
            return []
    
    def get_all_users_table(self) -> List[List[str]]:
        """Get all users from whitelist (whether logged in or not) for hierarchy table"""
        try:
            # Get ALL whitelist entries
            whitelist = self.supabase.table("email_whitelist")\
                .select("*")\
                .eq("is_active", True)\
                .order("added_at", desc=True)\
                .execute()
            
            if not whitelist.data:
                return []
            
            # Get users table for name/role/last_login
            users_data = self.supabase.table("users")\
                .select("*")\
                .execute()
            users_map = {u['email']: u for u in users_data.data} if users_data.data else {}
            
            table_data = []
            for item in whitelist.data:
                email = item['email']
                user_record = users_map.get(email)
                
                # Name: use from users table if exists, else extract from email
                if user_record and user_record.get('name'):
                    name = user_record['name']
                else:
                    name = email.split('@')[0].replace('.', ' ').title()
                
                # Role: from users table if exists, else default to 'user'
                role = user_record['role'].upper() if user_record else 'USER'
                
                # Added by
                added_by = item.get('added_by', 'system')
                
                # Last login - DATE ONLY
                if user_record and user_record.get('last_login'):
                    last_login = user_record['last_login']
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                        last_login_str = dt.strftime('%Y-%m-%d')
                    except:
                        last_login_str = last_login[:10] if len(last_login) >= 10 else 'Never'
                else:
                    last_login_str = 'Never'
                
                # Date added
                added_at = item.get('added_at', '')
                if added_at:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d')
                    except:
                        date_str = added_at[:10] if len(added_at) >= 10 else 'N/A'
                else:
                    date_str = 'N/A'
                
                # Format: [Name, Email, Role, Added By, Last Login, Date Added]
                table_data.append([name, email, role, added_by, last_login_str, date_str])
            
            return table_data
        except Exception as e:
            print(f"Error getting all users table: {e}")
            return []
    
    def get_users_by_role_table(self, role_filter: str) -> List[List[str]]:
        """Get filtered users with full details for role filtering"""
        try:
            if role_filter == "All":
                return self.get_all_users_table()
            else:
                # Filter by specific role
                all_users = self.get_all_users_table()
                filtered = [row for row in all_users if row[2] == role_filter.upper()]  # row[2] is Role column
                return filtered
        except Exception as e:
            print(f"Error getting users by role table: {e}")
            return []

# Global user management instance
user_management = UserManagement()