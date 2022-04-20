from MyModules import params


class WorkingDay:
    start = params.start
    end = params.end
    play = params.play
    tech_service = params.tech_service

    @staticmethod
    def time_in_str(float_hours: float):
        """Конвертирует запись времени в часах из типа float в строку формата 'ЧЧ:ММ'"""
        string_time = f"{float_hours // 1 :02.0f}:{float_hours % 1 * 60 // 1 :02.0f}"
        return string_time

    def timetable(self):
        """Возвращает расписание сеансов на день в формате списка времени в часах начала и окончания сеанса
        (float, float) исходя из известных параметров"""
        daily_schedule = []
        s_time = self.start
        while s_time <= self.end - self.play / 60:

            daily_schedule.append((self.time_in_str(s_time),
                                   self.time_in_str(s_time + self.play / 60)
                                   ))
            s_time += (self.play + self.tech_service) / 60
        return daily_schedule
