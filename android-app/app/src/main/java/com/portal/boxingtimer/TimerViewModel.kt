package com.portal.boxingtimer

import android.app.Application
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class TimerViewModel(application: Application) : AndroidViewModel(application) {

    data class TimerUiState(
        val remainingSeconds: Int = WORK_DURATION_SECONDS,
        val currentRound: Int = 1,
        val status: TimerService.TimerStatus = TimerService.TimerStatus.WORK,
        val isRunning: Boolean = false,
        val isFinished: Boolean = false
    )

    private val appContext = application.applicationContext

    private val _uiState = MutableStateFlow(TimerUiState())
    val uiState: StateFlow<TimerUiState> = _uiState.asStateFlow()

    private val timerStateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action != TimerService.ACTION_STATE_UPDATE) return

            val seconds = intent.getIntExtra(TimerService.EXTRA_REMAINING_SECONDS, WORK_DURATION_SECONDS)
            val round = intent.getIntExtra(TimerService.EXTRA_ROUND, 1)
            val statusName = intent.getStringExtra(TimerService.EXTRA_STATUS)
                ?: TimerService.TimerStatus.WORK.name
            val running = intent.getBooleanExtra(TimerService.EXTRA_IS_RUNNING, false)
            val finished = intent.getBooleanExtra(TimerService.EXTRA_IS_FINISHED, false)

            val status = runCatching { TimerService.TimerStatus.valueOf(statusName) }
                .getOrDefault(TimerService.TimerStatus.WORK)

            _uiState.value = TimerUiState(
                remainingSeconds = seconds,
                currentRound = round,
                status = status,
                isRunning = running,
                isFinished = finished
            )
        }
    }

    init {
        val filter = IntentFilter(TimerService.ACTION_STATE_UPDATE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            appContext.registerReceiver(timerStateReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("DEPRECATION")
            appContext.registerReceiver(timerStateReceiver, filter)
        }
    }

    fun startTimer() {
        sendServiceAction(TimerService.ACTION_START)
    }

    fun pauseTimer() {
        sendServiceAction(TimerService.ACTION_PAUSE)
    }

    fun resetTimer() {
        sendServiceAction(TimerService.ACTION_RESET)
    }

    private fun sendServiceAction(action: String) {
        val serviceIntent = Intent(appContext, TimerService::class.java).apply {
            this.action = action
        }
        ContextCompat.startForegroundService(appContext, serviceIntent)
    }

    fun formatTime(totalSeconds: Int): String {
        val minutes = totalSeconds / 60
        val seconds = totalSeconds % 60
        return String.format("%02d:%02d", minutes, seconds)
    }

    override fun onCleared() {
        appContext.unregisterReceiver(timerStateReceiver)
        super.onCleared()
    }

    companion object {
        private const val WORK_DURATION_SECONDS = 3 * 60
    }
}
