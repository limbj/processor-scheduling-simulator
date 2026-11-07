"""Behavior checks for the redesigned UI, using offscreen Qt widgets."""

import importlib.util
import os
import re
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
HAS_QT = importlib.util.find_spec("PyQt5") is not None

if HAS_QT:
    from PyQt5.QtCore import QPoint, QRect, QSize
    from PyQt5.QtGui import QIcon
    from PyQt5.QtWidgets import QApplication, QAbstractScrollArea, QMessageBox, QWidget

    import ui


@unittest.skipUnless(HAS_QT, "Install requirements.txt to run the GUI tests.")
class SchedulerDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        for name in ("warning", "critical", "about"):
            replacement = patch.object(QMessageBox, name, return_value=QMessageBox.Ok)
            replacement.start()
            self.addCleanup(replacement.stop)
        question = patch.object(QMessageBox, "question", return_value=QMessageBox.No)
        self.question = question.start()
        self.addCleanup(question.stop)
        self.window = ui.OS_Scheduler()
        self.window.cb_algorithm.setCurrentIndex(1)
        self.window.cb_core0.setCurrentIndex(1)

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QApplication.processEvents()

    def first_number(self, label):
        match = re.search(r"-?\d+(?:\.\d+)?", label.text())
        self.assertIsNotNone(match, "Expected a numeric label: %r" % label.text())
        return float(match.group())

    def assert_process_count(self, expected):
        self.assertEqual(int(self.first_number(self.window.lb_process_count)), expected)

    def assert_empty_metrics(self):
        for name in ("lb_average_wt", "lb_average_ntt", "lb_total_power"):
            with self.subTest(label=name):
                self.assertEqual(getattr(self.window, name).text().strip(), "—")
        self.assertFalse(self.window.lb_time_placeholder.isHidden())
        self.assertIn("대기", self.window.lb_run_status.text())

    def test_summary_metrics_match_engine_results_and_clear_together(self):
        self.assert_empty_metrics()
        self.assert_process_count(0)
        self.window.createProcessFunction(1, 0, 6)
        self.window.createProcessFunction(2, 0, 2)
        self.window.startFunction()
        result = self.window.last_result
        self.assertIsNotNone(result)
        self.assertAlmostEqual(
            self.first_number(self.window.lb_average_wt), result.average_waiting_time, places=2
        )
        self.assertAlmostEqual(
            self.first_number(self.window.lb_average_ntt),
            result.average_normalized_turnaround_time,
            places=2,
        )
        self.assertAlmostEqual(
            self.first_number(self.window.lb_total_power), result.total_power_usage, places=1
        )
        self.assertEqual(int(self.window.lb_time.text()), result.duration)
        self.assertTrue(self.window.lb_time_placeholder.isHidden())
        self.assertIn("완료", self.window.lb_run_status.text())
        self.assert_process_count(2)

        self.window.createProcessFunction(3, 1, 1)
        self.assert_empty_metrics()
        self.assert_process_count(3)

    def test_process_count_tracks_deletion_in_the_sorted_table(self):
        self.window.createProcessFunction(10, 1, 3)
        self.window.createProcessFunction(2, 0, 4)
        table = self.window.tw_process
        for row in range(table.rowCount()):
            if table.item(row, 0).text() == "P10":
                table.selectRow(row)
                break
        self.window.processRemoveFunction()
        self.assert_process_count(1)
        self.assertEqual([p.process_id for p in self.window.scheduler.processes], [2])

    def assert_scenario_selection_reset(self):
        self.assertIsNone(self.window.selected_model_flag)
        self.assertIsNone(self.window.selected_complexity_flag)
        for name in ("pb_model1", "pb_model2", "pb_high", "pb_mid", "pb_low"):
            self.assertFalse(getattr(self.window, name).isChecked(), name)
        self.assert_scenario_icons()

    def assert_scenario_icons(self, model=None, complexity=None):
        expected = (
            ("pb_model1", "gpt-icon.png" if model == 1 else "g_gpt-icon.png"),
            ("pb_model2", "gpt4-icon.png" if model == 2 else "g_gpt-icon.png"),
            ("pb_high", "complex.png" if complexity == 3 else "g_complex.png"),
            ("pb_mid", "complex.png" if complexity == 4 else "g_complex.png"),
            ("pb_low", "complex.png" if complexity == 5 else "g_complex.png"),
        )
        for name, image_name in expected:
            with self.subTest(button=name, image=image_name):
                button = getattr(self.window, name)
                state = QIcon.On if button.isChecked() else QIcon.Off
                actual = button.icon().pixmap(QSize(40, 40), QIcon.Normal, state).toImage()
                reference = ui.icon(image_name).pixmap(QSize(40, 40)).toImage()
                self.assertFalse(actual.isNull(), name)
                self.assertFalse(reference.isNull(), image_name)
                self.assertEqual(actual, reference, "%s should display %s" % (name, image_name))

    def test_drr_icons_follow_exclusive_selection_and_repeated_clicks(self):
        self.window.cb_algorithm.setCurrentIndex(6)
        self.assert_scenario_selection_reset()

        self.window.pb_model1.click()
        self.assertTrue(self.window.pb_model1.isChecked())
        self.assertFalse(self.window.pb_model2.isChecked())
        self.assert_scenario_icons(model=1)
        self.window.pb_model1.click()
        self.assertTrue(self.window.pb_model1.isChecked())
        self.assertEqual(self.window.selected_model_flag, 1)
        self.assert_scenario_icons(model=1)
        self.window.pb_model2.click()
        self.assertFalse(self.window.pb_model1.isChecked())
        self.assertTrue(self.window.pb_model2.isChecked())
        self.assertEqual(self.window.selected_model_flag, 2)
        self.assert_scenario_icons(model=2)

        # A complete selection prompts for generation; declining restores gray icons.
        self.window.pb_mid.click()
        self.question.assert_called_once()
        self.assertEqual(self.window.scheduler.processes, [])
        self.assert_scenario_selection_reset()

        self.window.pb_low.click()
        self.assertTrue(self.window.pb_low.isChecked())
        self.assertFalse(self.window.pb_mid.isChecked())
        self.assertFalse(self.window.pb_high.isChecked())
        self.assert_scenario_icons(complexity=5)
        self.window.pb_low.click()
        self.assertTrue(self.window.pb_low.isChecked())
        self.assertEqual(self.window.selected_complexity_flag, 5)
        self.assert_scenario_icons(complexity=5)
        self.window.pb_high.click()
        self.assertFalse(self.window.pb_low.isChecked())
        self.assertFalse(self.window.pb_mid.isChecked())
        self.assertTrue(self.window.pb_high.isChecked())
        self.assertEqual(self.window.selected_complexity_flag, 3)
        self.assert_scenario_icons(complexity=3)

    def test_drr_model_then_complexity_generates_three_expected_processes(self):
        self.window.cb_algorithm.setCurrentIndex(6)
        self.question.return_value = QMessageBox.Yes
        with patch("ui.random.randint", side_effect=lambda low, high: low):
            self.window.pb_model2.click()
            self.assertEqual(self.window.scheduler.processes, [])
            self.window.pb_mid.click()
        processes = self.window.scheduler.processes
        self.assertEqual(len(processes), 3)
        self.assertEqual([p.gpt_model for p in processes], ["GPT 4"] * 3)
        self.assertEqual([p.complexity for p in processes], [6] * 3)
        self.assertEqual([p.burst_time for p in processes], [12] * 3)
        self.question.assert_called_once()
        self.assert_process_count(3)
        self.assert_scenario_selection_reset()

    def test_drr_complexity_then_model_generates_three_expected_processes(self):
        self.window.cb_algorithm.setCurrentIndex(6)
        self.question.return_value = QMessageBox.Yes
        with patch("ui.random.randint", side_effect=lambda low, high: low):
            self.window.pb_low.click()
            self.assertEqual(self.window.scheduler.processes, [])
            self.window.pb_model1.click()
        processes = self.window.scheduler.processes
        self.assertEqual(len(processes), 3)
        self.assertEqual([p.gpt_model for p in processes], ["GPT 3.5"] * 3)
        self.assertEqual([p.complexity for p in processes], [1] * 3)
        self.assertEqual([p.burst_time for p in processes], [1] * 3)
        self.question.assert_called_once()
        self.assert_process_count(3)
        self.assert_scenario_selection_reset()

    def test_drr_generation_cancel_preserves_results_and_clears_selection(self):
        self.window.cb_algorithm.setCurrentIndex(6)
        self.window.createProcessFunction(1, 0, 6, "Manual", 6)
        self.window.startFunction()
        previous = self.window.last_result
        previous_summary = self.window.lb_total_power.text()
        self.window.pb_model1.click()
        self.window.pb_high.click()
        self.question.assert_called_once()
        self.assertIs(self.window.last_result, previous)
        self.assertEqual(self.window.lb_total_power.text(), previous_summary)
        self.assertEqual(len(self.window.scheduler.processes), 1)
        self.assert_process_count(1)
        self.assert_scenario_selection_reset()

    def test_rr_and_drr_controls_keep_their_original_enablement(self):
        for algorithm in (1, 2, 6, 3, 2):
            with self.subTest(algorithm=algorithm):
                self.window.cb_algorithm.setCurrentIndex(algorithm)
                self.assertEqual(not self.window.gb_Timeq.isHidden(), algorithm == 2)
                self.assertEqual(self.window.gb_model.isEnabled(), algorithm == 6)
                self.assertEqual(self.window.gb_complex.isEnabled(), algorithm == 6)
                self.assertEqual(self.window.gb_add.isEnabled(), algorithm != 6)
                self.assertEqual(self.window.pb_random.isEnabled(), algorithm != 6)
                self.assertTrue(self.window.lb_algorithm_hint.text().strip())
                if algorithm == 2:
                    self.window.sb_Timeq.setValue(7)
        self.assertEqual(self.window.sb_Timeq.value(), 7)
        self.assertEqual(self.window.time_quantum, 7)

    def test_minimum_desktop_layout_keeps_inputs_and_tables_accessible(self):
        self.window.resize(1080, 720)
        self.window.ensurePolished()
        self.window.layout().activate()
        for widget in [self.window.centralWidget()] + self.window.findChildren(QWidget):
            if widget.layout() is not None:
                widget.layout().activate()
        QApplication.processEvents()
        self.assertLessEqual(self.window.width(), 1080)
        self.assertLessEqual(self.window.height(), 720)

        names = (
            "pb_start", "cb_algorithm", "cb_core0", "cb_core1", "cb_core2", "cb_core3",
            "pb_savep", "pb_resetp", "pb_random", "lb_add_process", "lb_add_process_at",
            "lb_add_process_bt", "pb_up1", "pb_down1", "pb_up2", "pb_down2", "pb_up3",
            "pb_down3", "pb_model1", "pb_model2", "pb_high", "pb_mid", "pb_low",
            "tw_process", "tw_gantt", "tw_result",
        )
        for name in names:
            with self.subTest(control=name):
                widget = getattr(self.window, name)
                point = widget.mapTo(self.window, QPoint(0, 0))
                self.assertGreater(widget.width(), 0)
                self.assertGreater(widget.height(), 0)
                self.assertGreaterEqual(point.x(), 0)
                self.assertLessEqual(point.x() + widget.width(), self.window.width())
                ancestor = widget.parentWidget()
                in_scroller = False
                while ancestor is not None:
                    if isinstance(ancestor, QAbstractScrollArea):
                        in_scroller = True
                        break
                    ancestor = ancestor.parentWidget()
                if not in_scroller:
                    self.assertGreaterEqual(point.y(), 0)
                    self.assertLessEqual(point.y() + widget.height(), self.window.height())
        self.assertGreaterEqual(self.window.pb_start.width(), 100)
        self.assertGreaterEqual(self.window.pb_start.height(), 28)
        for table in (self.window.tw_process, self.window.tw_gantt, self.window.tw_result):
            self.assertGreaterEqual(table.width(), 360)

    def test_process_colors_are_painted_in_the_process_and_gantt_cells(self):
        self.assertEqual(QApplication.platformName(), "offscreen")
        self.window.createProcessFunction(1, 0, 6)
        self.window.startFunction()
        self.window.resize(1360, 940)
        self.window.show()
        QApplication.processEvents()
        # A stylesheet refresh must not replace the model's process colors.
        self.window.setStyleSheet(self.window.styleSheet())
        QApplication.processEvents()

        for table, column in ((self.window.tw_process, 0), (self.window.tw_gantt, 1)):
            with self.subTest(table=table.objectName()):
                table.clearSelection()
                item = table.item(0, column)
                table.scrollToItem(item)
                QApplication.processEvents()
                color = item.background().color()
                self.assertNotEqual(color.name(), "#ffffff")
                rect = table.visualItemRect(item).intersected(table.viewport().rect())
                rect.adjust(3, 3, -3, -3)
                self.assertFalse(rect.isEmpty())
                pixmap = table.viewport().grab()
                image = pixmap.toImage()
                scale = pixmap.devicePixelRatio()
                expected = color.rgb() & 0xFFFFFF
                matching = any(
                    image.pixel(x, y) & 0xFFFFFF == expected
                    for y in range(int(rect.top() * scale), int((rect.bottom() + 1) * scale))
                    for x in range(int(rect.left() * scale), int((rect.right() + 1) * scale))
                )
                self.assertTrue(
                    matching,
                    "The model color must remain visible after applying the stylesheet.",
                )

    def test_normal_desktop_layout_shows_process_core_and_result_rows(self):
        self.assertEqual(QApplication.platformName(), "offscreen")
        for index, core in enumerate((1, 1, 1, 2)):
            getattr(self.window, "cb_core%d" % index).setCurrentIndex(core)
        for pid in range(1, 11):
            self.window.createProcessFunction(pid, 0, 20)
        self.window.startFunction()
        self.window.resize(1360, 940)
        self.window.show()
        QApplication.processEvents()

        for table, required in (
            (self.window.tw_process, 7),
            (self.window.tw_gantt, 4),
            (self.window.tw_result, 4),
        ):
            with self.subTest(table=table.objectName()):
                table.scrollToTop()
                QApplication.processEvents()
                complete_rows = sum(
                    table.rowViewportPosition(row) >= 0
                    and table.rowViewportPosition(row) + table.rowHeight(row)
                    <= table.viewport().height()
                    for row in range(table.rowCount())
                )
                self.assertGreaterEqual(
                    complete_rows, required,
                    "The viewport should show the intended rows without inner scrolling.",
                )
        self.assertGreater(self.window.tw_gantt.horizontalScrollBar().maximum(), 0)

    def test_process_workspace_stays_left_of_settings_and_results(self):
        self.assertEqual(QApplication.platformName(), "offscreen")

        def widget_rect(widget):
            return QRect(widget.mapTo(self.window, QPoint(0, 0)), widget.size())

        def layout_rect(layout):
            geometry = layout.geometry()
            origin = layout.parentWidget().mapTo(self.window, geometry.topLeft())
            return QRect(origin, geometry.size())

        for width, height in ((1360, 940), (1080, 720)):
            with self.subTest(size=(width, height)):
                self.window.resize(width, height)
                self.window.show()
                QApplication.processEvents()
                left_cards = [widget_rect(getattr(self.window, name)) for name in (
                    "process_card", "gantt_card",
                )]
                right_cards = [widget_rect(getattr(self.window, name)) for name in (
                    "algorithm_card", "cores_card", "scenario_card", "result_card",
                )]
                for left in left_cards:
                    for right in right_cards:
                        self.assertLess(left.right(), right.left())
                self.assertLess(left_cards[0].bottom(), left_cards[1].top())
                for card in right_cards[:-1]:
                    self.assertLess(card.bottom(), right_cards[-1].top())
                for card in left_cards + right_cards:
                    self.assertGreaterEqual(card.left(), 0)
                    self.assertLess(card.right(), self.window.width())

                summary = layout_rect(self.window.summary_layout)
                body = layout_rect(self.window.body_layout)
                self.assertLess(summary.bottom(), body.top())
                self.assertLessEqual(summary.left(), left_cards[0].left())
                self.assertGreaterEqual(summary.right(), right_cards[-1].right())

                names = (
                    "lb_add_process", "lb_add_process_at", "lb_add_process_bt",
                    "pb_up1", "pb_down1", "pb_up2", "pb_down2", "pb_up3", "pb_down3",
                    "pb_resetp", "pb_savep",
                )
                controls = [(name, widget_rect(getattr(self.window, name))) for name in names]
                for index, (name, rect) in enumerate(controls):
                    self.assertGreaterEqual(rect.left(), 0, name)
                    self.assertLess(rect.right(), self.window.width(), name)
                    for other_name, other_rect in controls[index + 1:]:
                        self.assertFalse(rect.intersects(other_rect), "%s overlaps %s" % (name, other_name))


if __name__ == "__main__":
    unittest.main()
