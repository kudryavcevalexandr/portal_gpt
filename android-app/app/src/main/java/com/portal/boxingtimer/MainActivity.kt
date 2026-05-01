package com.portal.boxingtimer

import android.os.Bundle
import android.view.WindowManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private val viewModel: TimerViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        val rootLayout = findViewById<LinearLayout>(R.id.rootLayout)
        val timerText = findViewById<TextView>(R.id.tvTimer)
        val statusLabel = findViewById<TextView>(R.id.tvStatus)
        val roundsLabel = findViewById<TextView>(R.id.tvRounds)
        val btnStart = findViewById<Button>(R.id.btnStart)
        val btnReset = findViewById<Button>(R.id.btnReset)

        btnStart.setOnClickListener {
            val current = viewModel.uiState.value
            if (current.isRunning) {
                viewModel.pauseTimer()
            } else {
                viewModel.startTimer()
            }
        }

        btnReset.setOnClickListener {
            viewModel.resetTimer()
        }

        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    timerText.text = viewModel.formatTime(state.remainingSeconds)
                    roundsLabel.text = getString(R.string.round_format, state.currentRound, TOTAL_ROUNDS)

                    if (state.isFinished) {
                        statusLabel.text = getString(R.string.status_end)
                        val color = ContextCompat.getColor(this@MainActivity, R.color.black)
                        statusLabel.setTextColor(color)
                        timerText.setTextColor(color)
                        rootLayout.setBackgroundColor(
                            ContextCompat.getColor(this@MainActivity, R.color.finish_green)
                        )
                    } else {
                        val isWork = state.status == TimerService.TimerStatus.WORK
                        statusLabel.text = if (isWork) getString(R.string.status_work) else getString(R.string.status_rest)
                        val color = ContextCompat.getColor(
                            this@MainActivity,
                            if (isWork) R.color.work_green else R.color.rest_red
                        )
                        statusLabel.setTextColor(color)
                        timerText.setTextColor(color)
                        rootLayout.setBackgroundColor(
                            ContextCompat.getColor(this@MainActivity, R.color.black)
                        )
                    }

                    btnStart.text = if (state.isRunning) {
                        getString(R.string.btn_pause)
                    } else {
                        getString(R.string.btn_start)
                    }
                }
            }
        }
    }

    companion object {
        private const val TOTAL_ROUNDS = 12
    }
}
