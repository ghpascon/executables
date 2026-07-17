import logging

import httpx


class WriteCommands:
    async def get_write_cmd(self, tag):
        identifier = tag.target_identifier
        target = tag.target_value
        epc = tag.new_epc
        password = tag.password

        if identifier == "epc":
            logging.info(f"Get tid from -> {target}")
            tid_from_epc = await self.get_tid_from_epc(target)
            if tid_from_epc is not None:
                target = tid_from_epc
                logging.info(f"Using tid -> {target}")
                identifier = "tid"

        return {
            "accessCommands": [
                {
                    "identifier": "1",
                    "blockWrite": {
                        "memoryBank": "epc",
                        "wordOffset": 2,
                        "dataHex": epc[0:8],
                    },
                },
                {
                    "identifier": "2",
                    "blockWrite": {
                        "memoryBank": "epc",
                        "wordOffset": 4,
                        "dataHex": epc[8:16],
                    },
                },
                {
                    "identifier": "3",
                    "blockWrite": {
                        "memoryBank": "epc",
                        "wordOffset": 6,
                        "dataHex": epc[16:24],
                    },
                },
            ],
            "tagAccessPasswordHex": password,
            "tagSelectors": [
                {
                    "action": "include",
                    "tagMemoryBank": identifier if identifier else "epc",
                    "bitOffset": 0 if identifier == "tid" else 32,
                    "mask": target if target else "0",
                    "maskLength": 1 if identifier is None else 96,
                }
            ],
        }

    async def send_write_command(self, all_commands):
        if not isinstance(all_commands, list):
            all_commands = [all_commands]
        payload = {"accessConfigurations": all_commands}
        try:
            async with httpx.AsyncClient(auth=self.auth, verify=False, timeout=10.0) as session:
                await self.post_to_reader(session, self.endpoint_write, payload=payload)
        except Exception as e:
            logging.error(f"Failed to Write: {e}")
