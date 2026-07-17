import logging
from datetime import datetime

from pydantic import ValidationError
from pyepc import SGTIN

from app.schemas.tag import TagSchema
from app.db.database import database_engine
import json
from app.models.rfid import DbRfid
import httpx
from app.core.settings import settings

class OnEvent:
    async def on_tag(self, tag: dict, verbose: bool = True):
        """
        Handle a tag read event.

        Args:
            tag (dict): Raw tag data.
            verbose (bool): If True, log/print when a new tag is added.
        """
        try:
            # Validate incoming tag structure
            tag_validado = TagSchema(**tag)

            # Check if tag already exists
            tag_exist = False
            if tag_validado.epc in self.tags:
                self.tags[tag_validado.epc]["timestamp"] = datetime.now()
                tag_exist = True

            # If tag already exists, only update if stronger RSSI
            if tag_exist:
                if tag_validado.rssi is None or self.tags[tag_validado.epc].get("rssi") is not None:
                    return None
                if tag_validado.rssi <= self.tags[tag_validado.epc].get("rssi"):
                    return None

            # Try decoding GTIN from EPC
            try:
                gtin = SGTIN.decode(tag_validado.epc).gtin
            except Exception:
                gtin = ""

            # Build normalized tag object
            current_tag = {
                "timestamp": datetime.now(),
                "device": tag_validado.device,
                "epc": tag_validado.epc,
                "tid": tag_validado.tid,
                "ant": tag_validado.ant,
                "rssi": tag_validado.rssi,
                "gtin": gtin,
                "info": None
            }

            # Save tag
            self.tags[tag_validado.epc] = current_tag

            # Log only when new tag is detected
            if verbose and not tag_exist:
                logging.info(f"[TAG] {current_tag}")

        except ValidationError as e:
            logging.error(f"❌ Invalid tag: {e.json()}")

        finally:
            return None

    async def on_start(self, device: str) -> None:
        """
        Handle 'start inventory' event for a device.
        """
        logging.info(f"[ START ] -> Reader: {device}")

        self.start_inventory_timestamp = datetime.now()
        self.tags_saved = False
        
        await self.clear_tags(device)  # Clear tags for this device
        await self.on_event(device, "inventory", True)

    async def on_stop(self, device: str) -> None:
        """
        Handle 'stop inventory' event for a device.
        """
        logging.info(f"[ STOP ] -> Reader: {device}")
        self.start_inventory_timestamp = None
        await self.on_event(device, "inventory", False)
        return len(self.tags)

    async def on_event(self, device: str, event_type: str, event_data) -> None:
        """
        Handle a generic event.

        Args:
            device (str): Reader name.
            event_type (str): Event type (e.g., "tag", "inventory").
            event_data (Any): Event payload.
        """
        if event_type == "tag":
            await self.on_tag(event_data)
            return

        timestamp = datetime.now()
        if event_type == "esp":
            return await self.handle_esp_command(event_data)
        logging.info(f"[ EVENT ] - {timestamp} - {device} - {event_type} - {event_data}")

        return None

    async def on_connect(self, device: str) -> None:
        """Handle reader connection."""
        await self.on_event(device, "connection_event", True)

    async def on_disconnect(self, device: str) -> None:
        """Handle reader disconnection."""
        await self.on_event(device, "connection_event", False)

    async def handle_esp_command(self, data):
        #IGNORE
        if data.startswith("#tags_qty:") or data.startswith("#add:"):
            return None

        logging.info(data)

        #OPEN
        if data.startswith("#open:"):
            _,door = data.split(":")
            logging.info(f"[ OPEN ] -> {door}")
            await self.save_tags_on_open(int(door))
            

        #CLOSE
        if data.startswith("#close:"):
            _,door = data.split(":")
            logging.info(f"[ CLOSE  ] -> {door}")

        #WG
        if data.startswith("#wg:"):
            # expects "#wg:<door>:<card_id>"
            try:
                _, door, card_id = data.split(":")
            except ValueError:
                logging.info(f"Malformed data: {data}")
                return None

            if card_id and len(card_id) > 5:
                logging.info(f"[ CARD_ID ] -> {card_id} (door {door})")

                self.card_id = card_id
                user_data = await self.get_user_by_card(card_id)
                if user_data:
                    self.user_id = user_data.user_id
                    logging.info(f"[ AUTHORIZED ] {card_id} -> User: {self.user_id}")
                    return f"#authorized:{door}:{card_id}"
                logging.info(f"[ DENIED ] {card_id}")
                return f"#denied:{door}:{card_id}"
        
        #LOCK
        elif data.startswith("#lock:"):
            self.is_open = data.endswith('1')

            logging.info(f"[ LOCK ] -> {'IS OPEN' if self.is_open else 'IS CLOSED'}")

        return None

    async def save_tags_on_open(self, door: int):
        """
        Save all current tags to database when door opens.
        
        Args:
            door (int): Door identifier
        """
        tags = dict(self.tags)
        saved_tags = []
        
        if not tags:
            logging.info("[ SAVE_TAGS ] Nenhuma tag para salvar")
            return
            
        try:
            async with database_engine.get_db() as db:
                for tag in tags.values():
                    # Create DbRfid record for each tag
                    db_tag = DbRfid(
                        timestamp=tag.get("timestamp"),
                        device=tag.get("device", "UNKNOWN"),
                        epc=tag.get("epc"),
                        door=door,
                        user_id=self.user_id or ""
                    )
                    db.add(db_tag)
                    saved_tags.append(tag.get("epc"))
                
                await db.commit()

            logging.info("*" * 20)
            logging.info(f"[ SAVE_TAGS ] {len(saved_tags)} tags salvas no banco para porta {door}")
            logging.info(f"[ SAVE_TAGS ] EPCs salvos: {saved_tags}")
            logging.info("*" * 20)

        except Exception as e:
            logging.error(f"[ SAVE_TAGS ] Erro ao salvar tags no banco: {e}")
            # O rollback é automaticamente feito pelo context manager database_engine.get_db()        

 
    async def fetch_descriptions(self, payload: dict):
        """
        Fetch descriptions for tags with missing info.

        Args:
            payload (dict): Payload containing device and list of EPCs.
        """
        if not payload.get("tags"):
            return
        
        tags_with_missing_info: list = payload.get("tags", [])

        url = self.msgas_api_url + "/rfidtag"
        user = settings.data.get("MSGAS_API_USER", "ApiSmartX")
        password = settings.data.get("MSGAS_API_PASSWORD", "@p1smtx2026")

        try:
            logging.info(f"[ FETCH_DESCRIPTIONS ] Payload: {payload}")
            async with httpx.AsyncClient(
                timeout=10.0,
                auth=httpx.BasicAuth(user, password)
            ) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                descriptions = json.loads(response.text)
                for info in descriptions:
                    epc = info.get("tag")
                    if epc in self.tags:
                        self.tags[epc]["info"] = info
                        logging.info(f"[ FETCH_DESCRIPTIONS ] Updated tag {epc} with info: {info}")
                        try:
                            tags_with_missing_info.remove(epc)
                        except ValueError:
                            logging.warning(f"[ FETCH_DESCRIPTIONS ] EPC {epc} not found in tags_with_missing_info")
            for tag in tags_with_missing_info:
                if tag in self.tags:
                    self.tags[tag]["info"] = {"descricao": "Produto não encontrado", "tag": tag}
                    logging.warning(f"[ FETCH_DESCRIPTIONS ] No info found for EPC: {tag}")

        except Exception as e:
            logging.error(f"[ FETCH_DESCRIPTIONS ] Error fetching descriptions: {e}")