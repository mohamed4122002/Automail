from uuid import UUID
from typing import BinaryIO
import csv
import io
from ..models import ContactList, Contact
from ..schemas.contacts import ContactListCreate

class ContactService:
    def __init__(self):
        pass

    async def create_list(self, list_in: ContactListCreate, owner_id: UUID) -> ContactList:
        contact_list = ContactList(
            name=list_in.name,
            description=list_in.description,
            owner_id=owner_id
        )
        await contact_list.insert()
        return contact_list

    async def get_lists(self, owner_id: UUID) -> list[ContactList]:
        return await ContactList.find(ContactList.owner_id == owner_id).to_list()

    async def import_contacts_from_csv(self, contact_list_id: UUID, file_content: str):
        # Synchronization handled by Celery task ideally, but logic resides here or is called by task
        # This function parses CSV content
        reader = csv.DictReader(io.StringIO(file_content))
        
        objects = []
        for row in reader:
            # Basic mapping
            email = row.get("email")
            if not email: continue
            
            c = Contact(
                contact_list_id=contact_list_id,
                email=email,
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                attributes=row # Store all CSV columns as JSONB attributes
            )
            objects.append(c)
        
        if objects:
            await Contact.insert_many(objects)
        
        return len(objects)
