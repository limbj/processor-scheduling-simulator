"""GUI regressions using real Qt widgets without opening desktop windows."""

import importlib.util
import os
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
HAS_QT = importlib.util.find_spec("PyQt5") is not None

if HAS_QT:
    from PyQt5.QtCore import QItemSelectionModel, Qt
    from PyQt5.QtWidgets import QApplication, QAbstractItemView, QMessageBox

    import ui


@unittest.skipUnless(HAS_QT, "Install requirements.txt to run the GUI tests.")
class SchedulerGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.dialogs = {}
        for name in ("warning", "critical", "about", "question"):
            replacement = patch.object(QMessageBox, name, return_value=QMessageBox.No)
            self.dialogs[name] = replacement.start()
            self.addCleanup(replacement.stop)
        self.window = ui.OS_Scheduler()
        self.window.cb_algorithm.setCurrentIndex(1)
        self.window.cb_core0.setCurrentIndex(1)

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QApplication.processEvents()

    def add(self, pid, at=0, bt=6):
        self.window.createProcessFunction(pid, at, bt, "Manual", min(bt, 30))

    def rows(self):
        table = self.window.tw_process
        return {
            table.item(row, 0).text(): tuple(
                table.item(row, column).text() if table.item(row, column) else None
                for column in (1, 2)
            )
            for row in range(table.rowCount())
        }

    def select_pid(self, pid, append=False):
        table = self.window.tw_process
        for row in range(table.rowCount()):
            if table.item(row, 0).data(Qt.UserRole) == pid:
                flags = QItemSelectionModel.Select | QItemSelectionModel.Rows
                if not append:
                    flags |= QItemSelectionModel.Clear
                table.selectionModel().select(table.model().index(row, 0), flags)
                return
        self.fail("PID %s is not present in the process table" % pid)

    def seed_result(self, algorithm=1, all_cores=False):
        self.window.cb_algorithm.setCurrentIndex(algorithm)
        if all_cores:
            for index, value in enumerate((1, 1, 1, 2)):
                getattr(self.window, "cb_core%d" % index).setCurrentIndex(value)
        self.add(1)
        self.window.startFunction()
        self.assertIsNotNone(self.window.last_result)
        self.assertEqual(self.window.tw_result.rowCount(), 1)
        self.assertGreater(self.window.tw_gantt.columnCount(), 1)
        self.assertNotEqual(self.window.label_3.text(), "0.0 W")
        return self.window.last_result

    def assert_output_cleared(self):
        self.assertIsNone(self.window.last_result)
        self.assertEqual(self.window.tw_result.rowCount(), 0)
        self.assertEqual(self.window.tw_gantt.columnCount(), 1)
        self.assertEqual(self.window.tw_gantt.rowCount(), sum(bool(v) for v in self.window.core))
        self.assertEqual(self.window.lb_time.text(), "")
        self.assertEqual(self.window.lb_sec.text(), "")
        self.assertEqual(self.window.statusBar().currentMessage(), "")
        for name in ("label_3", "label_5", "label_8", "label_9"):
            self.assertEqual(getattr(self.window, name).text(), "0.0 W")

    def test_random_generation_reuses_gaps_without_duplicate_pids(self):
        for pid in (1, 2, 3):
            self.add(pid)
        self.select_pid(2)
        self.window.processRemoveFunction()
        with patch("ui.random.randint", side_effect=lambda low, high: low):
            self.window.RandomAddProcessFunction()
        pids = [p.process_id for p in self.window.scheduler.processes]
        self.assertEqual(sorted(pids), [1, 2, 3, 4, 5])
        self.assertEqual(len(pids), len(set(pids)))
        self.assertEqual(self.window.addProcessName, 6)
        result = self.window.sendInfoToAlgorithmFunction()
        self.assertEqual(len(result.process_results), 5)

    def test_drr_generation_avoids_sparse_manual_ids(self):
        self.window.cb_algorithm.setCurrentIndex(6)
        for pid in (1, 3, 4, 10):
            self.add(pid)
        self.window.selected_model_flag = 2
        self.window.selected_complexity_flag = 5
        with patch("ui.random.randint", side_effect=lambda low, high: low):
            self.window.RandomAddProcessFunction(True)
        processes = self.window.scheduler.processes
        self.assertEqual(sorted(p.process_id for p in processes), [1, 2, 3, 4, 5, 6, 10])
        self.assertEqual([p.gpt_model for p in processes[-3:]], ["GPT 4"] * 3)
        self.assertEqual([p.burst_time for p in processes[-3:]], [2] * 3)
        self.assertEqual(len(self.window.sendInfoToAlgorithmFunction().process_results), 7)

    def test_sorted_insertion_preserves_each_process_values_and_color(self):
        for column in range(3):
            for order in (Qt.AscendingOrder, Qt.DescendingOrder):
                with self.subTest(column=column, order=order):
                    window = ui.OS_Scheduler()
                    self.addCleanup(window.close)
                    table = window.tw_process
                    table.setSortingEnabled(True)
                    table.sortItems(column, order)
                    expected = ((1, 7, 9), (2, 1, 3), (10, 4, 5))
                    for pid, at, bt in expected:
                        window.createProcessFunction(pid, at, bt)
                    self.assertTrue(table.isSortingEnabled())
                    actual = {}
                    for row in range(table.rowCount()):
                        item = table.item(row, 0)
                        pid = item.data(Qt.UserRole)
                        actual[pid] = tuple(int(table.item(row, c).text()) for c in (1, 2))
                        self.assertEqual(item.background().color(), window.scheduler.get_process_color(pid))
                    self.assertEqual(actual, {pid: (at, bt) for pid, at, bt in expected})

    def test_insertion_keeps_sorting_disabled_when_it_was_disabled(self):
        self.window.tw_process.setSortingEnabled(False)
        self.add(2, 7, 9)
        self.add(1, 1, 3)
        self.assertFalse(self.window.tw_process.isSortingEnabled())
        self.assertEqual(self.rows(), {"P02": ("07", "09"), "P01": ("01", "03")})

    def test_process_result_and_gantt_tables_are_read_only_but_selectable(self):
        self.seed_result()
        for table in (self.window.tw_process, self.window.tw_result, self.window.tw_gantt):
            with self.subTest(table=table.objectName()):
                self.assertEqual(table.editTriggers(), QAbstractItemView.NoEditTriggers)
                for row in range(table.rowCount()):
                    for column in range(table.columnCount()):
                        item = table.item(row, column)
                        if item is not None:
                            self.assertFalse(item.flags() & Qt.ItemIsEditable)
                            self.assertTrue(item.flags() & Qt.ItemIsSelectable)
        self.select_pid(1)
        self.window.processRemoveFunction()
        self.assertEqual(self.window.scheduler.processes, [])

    def test_result_waiting_and_turnaround_columns_sort_two_digit_numbers(self):
        self.window.cb_core0.setCurrentIndex(2)
        for pid, burst in ((1, 2), (2, 8), (3, 1)):
            self.add(pid, bt=burst)
        self.window.startFunction()
        self.assertIsNotNone(self.window.last_result)
        table = self.window.tw_result
        for column, expected in ((3, ["0", "2", "10"]), (4, ["2", "10", "11"])):
            for order in (Qt.AscendingOrder, Qt.DescendingOrder):
                with self.subTest(column=column, order=order):
                    table.sortItems(column, order)
                    actual = [table.item(row, column).text() for row in range(table.rowCount())]
                    self.assertEqual(actual, expected if order == Qt.AscendingOrder else expected[::-1])

    def test_result_arrival_and_burst_columns_sort_numerically(self):
        self.window.cb_core0.setCurrentIndex(2)
        for pid, arrival, burst in ((1, 2, 12), (2, 10, 2), (3, 1, 3)):
            self.add(pid, at=arrival, bt=burst)
        self.window.startFunction()
        self.assertIsNotNone(self.window.last_result)
        table = self.window.tw_result
        for column, expected in ((1, ["1", "2", "10"]), (2, ["2", "3", "12"])):
            for order in (Qt.AscendingOrder, Qt.DescendingOrder):
                with self.subTest(column=column, order=order):
                    table.sortItems(column, order)
                    actual = [table.item(row, column).text() for row in range(table.rowCount())]
                    self.assertEqual(actual, expected if order == Qt.AscendingOrder else expected[::-1])

    def test_result_ntt_sorts_decimals_numerically_and_keeps_two_decimal_places(self):
        self.window.cb_core0.setCurrentIndex(2)
        for pid, burst in ((1, 3), (2, 2), (3, 5), (4, 1)):
            self.add(pid, bt=burst)
        self.window.startFunction()
        self.assertIsNotNone(self.window.last_result)
        table = self.window.tw_result
        expected = ["1.00", "2.00", "2.50", "11.00"]
        for order in (Qt.AscendingOrder, Qt.DescendingOrder):
            with self.subTest(order=order):
                table.sortItems(5, order)
                actual = [table.item(row, 5).text() for row in range(table.rowCount())]
                self.assertEqual(actual, expected if order == Qt.AscendingOrder else expected[::-1])

    def test_sorted_terminated_results_preserve_out_label_tooltips_and_readonly_flags(self):
        self.window.cb_algorithm.setCurrentIndex(6)
        self.add(1, bt=35)
        self.add(2, bt=2)
        self.window.startFunction()
        result = self.window.last_result
        self.assertIsNotNone(result)
        self.assertEqual([process.pid for process in result.terminated], [1])
        table = self.window.tw_result
        table.sortItems(3, Qt.AscendingOrder)
        found_terminated = False
        for row in range(table.rowCount()):
            terminated = table.item(row, 0).text() == "P01 (OUT)"
            found_terminated |= terminated
            self.assertRegex(table.item(row, 5).text(), r"^\d+\.\d{2}$")
            for column in range(table.columnCount()):
                item = table.item(row, column)
                self.assertFalse(item.flags() & Qt.ItemIsEditable)
                self.assertTrue(item.flags() & Qt.ItemIsSelectable)
                if terminated:
                    self.assertIn("강제 종료", item.toolTip())
        self.assertTrue(found_terminated)

    def test_delete_uses_stable_identity_even_if_display_label_changes(self):
        self.add(1)
        self.add(3)
        table = self.window.tw_process
        for row in range(table.rowCount()):
            if table.item(row, 0).data(Qt.UserRole) == 1:
                table.item(row, 0).setText("display label")
        self.select_pid(1)
        self.window.processRemoveFunction()
        self.assertEqual([p.process_id for p in self.window.scheduler.processes], [3])
        self.assertEqual(list(self.rows()), ["P03"])

    def test_deleting_sorted_multiple_rows_keeps_table_and_model_in_sync(self):
        for pid in (1, 3, 10):
            self.add(pid)
        self.window.tw_process.sortItems(0, Qt.DescendingOrder)
        self.select_pid(1)
        self.select_pid(10, append=True)
        self.window.processRemoveFunction()
        self.assertEqual([p.process_id for p in self.window.scheduler.processes], [3])
        self.assertEqual(list(self.rows()), ["P03"])

    def test_adding_a_process_clears_all_previous_results(self):
        self.seed_result()
        self.add(2)
        self.assert_output_cleared()

    def test_deleting_a_process_clears_all_previous_results(self):
        self.seed_result()
        self.select_pid(1)
        self.window.processRemoveFunction()
        self.assert_output_cleared()

    def test_switching_algorithm_clears_all_previous_results(self):
        self.seed_result()
        self.window.cb_algorithm.setCurrentIndex(2)
        self.assert_output_cleared()

    def test_core_change_clears_results_and_keeps_current_core_preview(self):
        self.seed_result()
        self.window.cb_core0.setCurrentIndex(2)
        self.assert_output_cleared()
        self.assertEqual(self.window.tw_gantt.item(0, 0).text(), "Core 0(E)")

    def test_rr_quantum_change_clears_all_previous_results(self):
        self.seed_result(algorithm=2)
        self.window.sb_Timeq.setValue(3)
        self.assertEqual(self.window.time_quantum, 3)
        self.assert_output_cleared()

    def test_failed_rerun_does_not_leave_previous_results(self):
        self.seed_result()
        with patch.object(self.window, "sendInfoToAlgorithmFunction", side_effect=RuntimeError("test failure")):
            self.window.startFunction()
        self.assert_output_cleared()
        self.dialogs["critical"].assert_called_once()

    def test_invalid_run_clears_previous_results_before_validation(self):
        self.seed_result()
        self.window.core = [0, 0, 0, 0]
        self.window.startFunction()
        self.assert_output_cleared()
        self.dialogs["warning"].assert_called_once()

    def test_rejected_core_selection_keeps_valid_previous_results(self):
        result = self.seed_result(all_cores=True)
        self.window.cb_core3.setCurrentIndex(1)
        self.assertEqual(self.window.core, [1, 1, 1, 2])
        self.assertEqual(self.window.cb_core3.currentIndex(), 2)
        self.assertIs(self.window.last_result, result)
        self.assertEqual(self.window.tw_result.rowCount(), 1)
        self.dialogs["warning"].assert_called_once()

    def test_rejected_manual_add_keeps_previous_results_and_inputs(self):
        result = self.seed_result()
        self.window.addProcessName = 1
        self.window.addBurstTime = 6
        self.window.processAddFunction(8)
        self.assertIs(self.window.last_result, result)
        self.assertEqual(len(self.window.scheduler.processes), 1)
        self.dialogs["warning"].assert_called_once()

    def test_manual_unused_pid_is_respected_and_draft_controls_keep_result(self):
        result = self.seed_result()
        for flag in (1, 3, 5, 7):
            self.window.processAddFunction(flag)
            self.assertIs(self.window.last_result, result)
        self.window.addProcessName = 10
        self.window.addArrivalTime = 2
        self.window.addBurstTime = 3
        self.window.processAddFunction(8)
        self.assertEqual([p.process_id for p in self.window.scheduler.processes], [1, 10])
        self.assertEqual(self.window.addProcessName, 2)
        self.assert_output_cleared()

    def test_duplicate_creation_does_not_leave_a_partial_table_row(self):
        self.add(1)
        with self.assertRaises(ValueError):
            self.add(1, 2, 3)
        self.assertEqual(self.window.tw_process.rowCount(), 1)
        self.assertEqual(len(self.window.scheduler.processes), 1)


if __name__ == "__main__":
    unittest.main()
