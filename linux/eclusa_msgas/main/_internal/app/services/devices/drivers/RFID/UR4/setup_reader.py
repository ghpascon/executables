import asyncio
import logging
import time


class SetupReader:
    async def setup_reader(self):
        await asyncio.sleep(0.5)
        logging.info("[SETUP] Iniciando setup")
        self.setup_step = 0
        self.setup = False
        self.wait_answer = False
        self.is_reading = False
        while True:
            await asyncio.sleep(0.05)
            if self.setup:
                await asyncio.sleep(5)
                continue
            await self.check_error_response()

            # REGIAO
            if self.setup_step == 0 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_region()
                self.wait_answer = True

            # INVENTORY MODE
            elif self.setup_step == 1 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_inventory_mode()
                self.wait_answer = True

            # SESSION + TARGET
            elif self.setup_step == 2 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_session_target()
                self.wait_answer = True

            # ANTENAS
            elif self.setup_step == 3 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_antennas()
                self.wait_answer = True

            # COMMAND MODE
            elif self.setup_step == 4 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_command_mode()
                self.wait_answer = True

            # TAG FOCUS
            elif self.setup_step == 5 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_tag_focus()
                self.wait_answer = True

            # FASTID
            elif self.setup_step == 6 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_fastid_1()
                self.wait_answer = True
            elif self.setup_step == 7 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_fastid_2()
                self.wait_answer = True
            elif self.setup_step == 8 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_fastid_3()
                self.wait_answer = True

            # FAST INVENTORY
            elif self.setup_step == 9 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_fast_inventory()
                self.wait_answer = True

            # BUZZER
            elif self.setup_step == 10 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_buzzer()
                self.wait_answer = True

            # RF-LINK
            elif self.setup_step == 11 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_rf_link()
                self.wait_answer = True

            # CW
            elif self.setup_step == 12 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.setup_cw()
                self.wait_answer = True

            # SET GPO
            elif self.setup_step == 13 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                await self.write_gpo({"state": False})
                self.wait_answer = True

            # POWER 1
            elif self.setup_step == 14 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                self.wait_answer = True
                await self.setup_power_ant(1)

            # POWER 2
            elif self.setup_step == 15 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                self.wait_answer = True
                await self.setup_power_ant(2)

            # POWER 3
            elif self.setup_step == 16 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                self.wait_answer = True
                await self.setup_power_ant(3)

            # POWER 4
            elif self.setup_step == 17 and not self.wait_answer:
                logging.info(f"[SETUP] Step -> {self.setup_step}")
                self.wait_answer = True
                await self.setup_power_ant(4)

            # END SETUP
            elif not self.wait_answer:
                self.setup = True

                logging.info("[SETUP] ✅ Setup Concluido")
                if self.config.get("START_READING"):
                    await self.start_inventory()

    ##############################################################################################################

    async def check_error_response(self):
        if self.setup:
            return
        current_ms = int(time.time() * 1000)
        self.current_timeout_answer = (
            current_ms if not self.wait_answer else self.current_timeout_answer
        )
        if current_ms > self.current_timeout_answer + self.timeout_answer:
            self.setup_step = 0
            self.setup = False
            self.wait_answer = False
            self.is_connected = False

    async def setup_region(self):
        await self.send_data([0xA5, 0x5A, 0x00, 0x0A, 0x2C, 0x01, 0x3C, 0x00, 0x0D, 0x0A])

    async def setup_inventory_mode(self):
        await self.send_data(
            [0xA5, 0x5A, 0x00, 0x0C, 0x70, 0x01, 0x01, 0x00, 0x00, 0x00, 0x0D, 0x0A]
        )

    async def setup_session_target(self):
        session = self.config.get("SESSION", 0)
        target = 0

        translate_dict = {"a": session, "b": {0: 0x3, 1: 0xB}}

        ab = (translate_dict["a"] << 4) | translate_dict["b"][target]

        data = [0xA5, 0x5A, 0x00, 0x0C, 0x20, 0x01, 0x60, 0xF4, ab, 0x00, 0x0D, 0x0A]
        await self.send_data(data)

    async def setup_antennas(self):
        b_antenas = 0
        antenna = self.config.get("ANT")
        if antenna is not None:
            for i in range(self.ant_qtd):
                ant_n = antenna.get(str(i + 1))
                if ant_n is None:
                    continue
                active = ant_n.get("active")
                if active is None or not active:
                    continue
                b_antenas |= 0x1 << (i)
        if b_antenas == 0:
            b_antenas = 1

        await self.send_data(
            [
                0xA5,
                0x5A,
                0x00,
                0x0D,
                0x28,
                0x01,
                0x00,
                b_antenas,
                0x00,
                0x00,
                0x00,
                0x0D,
                0x0A,
            ]
        )

    async def setup_command_mode(self):
        await self.send_data([0xA5, 0x5A, 0x00, 0x0A, 0xA1, 0x05, 0x00, 0x00, 0x0D, 0x0A])

    async def setup_tag_focus(self):
        await self.send_data([0xA5, 0x5A, 0x00, 0x0A, 0x60, 0x00, 0x00, 0x00, 0x0D, 0x0A])

    async def setup_fastid_1(self):
        await self.send_data([0xA5, 0x5A, 0x00, 0x0A, 0x5C, 0x01, 0x00, 0x00, 0x0D, 0x0A])

    async def setup_fastid_2(self):
        await self.send_data([0xA5, 0x5A, 0x00, 0x0A, 0x60, 0x00, 0x00, 0x00, 0x0D, 0x0A])

    async def setup_fastid_3(self):
        await self.send_data(
            [0xA5, 0x5A, 0x00, 0x0C, 0x70, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0D, 0x0A]
        )

    async def setup_fast_inventory(self):
        await self.send_data([0xA5, 0x5A, 0x00, 0x0A, 0x64, 0x01, 0x00, 0x00, 0x0D, 0x0A])

    async def setup_buzzer(self):
        buzzer = self.config.get("BUZZER", False)
        await self.send_data(
            [0xA5, 0x5A, 0x00, 0x0A, 0xA1, 0x07, 1 if buzzer else 0, 0x00, 0x0D, 0x0A]
        )

    async def setup_rf_link(self):
        await self.send_data([0xA5, 0x5A, 0x00, 0x0B, 0x52, 0x00, 0x01, 0x05, 0x00, 0x0D, 0x0A])

    async def setup_cw(self):
        await self.send_data([0xA5, 0x5A, 0x00, 0x09, 0x24, 0x01, 0x00, 0x0D, 0x0A])

    async def setup_power_ant(self, ant=1):
        try:
            if not self.config.get("ANT").get(str(ant)).get("active"):
                raise Exception(f"ANT {ant} not active")
            power = self.config.get("ANT").get(str(ant)).get("power")
            power = max(self.min_power, min(self.max_power, power))
            value = power * 100
            high = (value >> 8) & 0xFF
            low = value & 0xFF
            logging.info("send")
            await self.send_data(
                [
                    0xA5,
                    0x5A,
                    0x00,
                    0x0E,
                    0x10,
                    0x02,
                    ant,
                    high,
                    low,
                    high,
                    low,
                    0x00,
                    0x0D,
                    0x0A,
                ]
            )

        except Exception as e:
            logging.info(e)
            self.setup_step += 1
            self.wait_answer = False
