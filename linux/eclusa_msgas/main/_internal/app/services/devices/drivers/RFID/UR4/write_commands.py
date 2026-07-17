import asyncio
import logging

from app.schemas.tag import WriteTagValidator


class WriteCommands:
    async def write_epc(self, tag_command: dict, exist=False, clear=True):
        """
        Writes a new EPC (Electronic Product Code) to RFID tags.

        Args:
            tag_commands (dict): A dictionary or a list of dictionaries containing tag information.
                Each dictionary must have the following keys:
                    - target_identifier (str): The identifier type used to locate the tag ("EPC", "TID", None).
                    - target_value (str): The current value of the target identifier to find the tag.
                    - new_epc (str): The new EPC value to be written to the tag.
                    - password (str): The password to access the tag.

        Example:
            tag_commands = {
                    "target_identifier": "epc",
                    "target_value": "300833B2DDD9014000000001",
                    "new_epc": "300833B2DDD9014000000002",
                    "password": "00000000"
                }

        Notes:
            If a single dictionary is provided, it will be automatically converted into a list.
        """
        try:
            validated = WriteTagValidator(**tag_command)

            # TID FROM EPC
            if validated.target_identifier == "epc":
                logging.info(f"Get tid from -> {validated.target_value}")
                tid_from_epc = await self.get_tid_from_epc(validated.target_value)
                if tid_from_epc is not None:
                    validated.target_value = tid_from_epc
                    logging.info(f"Using tid -> {validated.target_value}")
                    validated.target_identifier = "tid"

            # SAVE TAG TO WRITE
            if validated.target_identifier == "tid" and not exist:
                tag_cmd = {
                    "target_identifier": validated.target_identifier,
                    "target_value": validated.target_value,
                    "new_epc": validated.new_epc,
                    "password": validated.password,
                }
                self.tags_to_write[validated.target_value] = {
                    "target": validated.new_epc,
                    "retry": self.config.get("WRITE_RETRY_COUNT"),
                    "tag_cmd": tag_cmd,
                }
                logging.info("Tag To Write -> ", self.tags_to_write[validated.target_value])

            # STOP READING BEFORE WRITE
            if self.is_reading:
                await self.send_data([0xA5, 0x5A, 0x00, 0x08, 0x8C, 0x00, 0x0D, 0x0A])
                await self.send_data([0xA5, 0x5A, 0x00, 0x09, 0x8D, 0x01, 0x00, 0x0D, 0x0A])
                await asyncio.sleep(0.5)

            # NO TARGET
            if validated.target_identifier is None:
                new_epc_bytes = await self.get_bytes_from_str(validated.new_epc)
                data = [
                    0xA5,
                    0x5A,
                    0x00,
                    0x22,
                    0x86,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x01,
                    0x00,
                    0x20,
                    0x00,
                    0x00,
                    0x01,
                    0x00,
                    0x02,
                    0x00,
                    0x06,
                    *new_epc_bytes,
                    0x00,
                    0x0D,
                    0x0A,
                ]
                await self.send_data(data)

            # EPC TARGET
            elif validated.target_identifier == "epc":
                new_epc_bytes = await self.get_bytes_from_str(validated.new_epc)
                target__bytes = await self.get_bytes_from_str(validated.target_value)
                data = [
                    0xA5,
                    0x5A,
                    0x00,
                    0x2E,
                    0x86,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x01,
                    0x00,
                    0x20,
                    0x00,
                    0x60,
                    *target__bytes,
                    0x01,
                    0x00,
                    0x02,
                    0x00,
                    0x06,
                    *new_epc_bytes,
                    0x00,
                    0x0D,
                    0x0A,
                ]
                await self.send_data(data)

            # TID TARGET
            elif validated.target_identifier == "tid":
                new_epc_bytes = await self.get_bytes_from_str(validated.new_epc)
                target__bytes = await self.get_bytes_from_str(validated.target_value)
                data = [
                    0xA5,
                    0x5A,
                    0x00,
                    0x2E,
                    0x86,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x02,
                    0x00,
                    0x00,
                    0x00,
                    0x60,
                    *target__bytes,
                    0x01,
                    0x00,
                    0x02,
                    0x00,
                    0x06,
                    *new_epc_bytes,
                    0x00,
                    0x0D,
                    0x0A,
                ]
                await self.send_data(data)

            # RESUME READING AFTER WRITE
            if self.is_reading:
                await asyncio.sleep(0.5)
                await self.send_data([0xA5, 0x5A, 0x00, 0x0A, 0x82, 0x00, 0x00, 0x00, 0x0D, 0x0A])

            if clear:
                await asyncio.sleep(0.3)
                await self.clear_tags()

        except Exception as e:
            logging.error(e)

    async def get_bytes_from_str(self, word: str) -> list[int]:
        """
        Converte uma string hexadecimal em uma lista de inteiros (bytes).
        Exemplo: "300833B2DDD9014000000002" => [0x30, 0x08, 0x33, ...]
        """
        word = word.strip()
        if len(word) % 2 != 0:
            word = "0" + word  # Garante número par de caracteres

        return [int(word[i : i + 2], 16) for i in range(0, len(word), 2)]
