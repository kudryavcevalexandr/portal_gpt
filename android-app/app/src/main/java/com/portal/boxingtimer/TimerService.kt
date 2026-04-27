package com.portal.boxingtimer

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.media.MediaPlayer
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class TimerService : Service() {

    enum class TimerStatus {
        WORK,
        REST
    }

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var timerJob: Job? = null

    private var currentRound = 1
    private var status = TimerStatus.WORK
    private var remainingSeconds = WORK_DURATION_SECONDS
    private var playedEnd10 = false

    private var startPlayer: MediaPlayer? = null
    private var punchPlayer: MediaPlayer? = null
    private var end10Player: MediaPlayer? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        initPlayers()
        startForeground(NOTIFICATION_ID, buildNotification())
        broadcastState()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startTimer()
            ACTION_PAUSE -> pauseTimer()
            ACTION_RESET -> resetTimer()
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        timerJob?.cancel()
        releasePlayers()
        super.onDestroy()
    }

    private fun startTimer() {
        if (timerJob?.isActive == true) return

        if (remainingSeconds == WORK_DURATION_SECONDS && status == TimerStatus.WORK) {
            playStartSound()
        }

        timerJob = serviceScope.launch {
            while (isActive) {
                delay(1_000)
                if (remainingSeconds > 0) {
                    remainingSeconds -= 1
                    if (status == TimerStatus.WORK && remainingSeconds == 10 && !playedEnd10) {
                        playEnd10Sound()
                        playedEnd10 = true
                    }
                }

                if (remainingSeconds <= 0) {
                    moveToNextPhase()
                }
                broadcastState()
                updateNotification()
            }
        }
    }

    private fun pauseTimer() {
        timerJob?.cancel()
        timerJob = null
        broadcastState()
        updateNotification()
    }

    private fun resetTimer() {
        timerJob?.cancel()
        timerJob = null
        currentRound = 1
        status = TimerStatus.WORK
        remainingSeconds = WORK_DURATION_SECONDS
        playedEnd10 = false
        broadcastState()
        updateNotification()
    }

    private fun moveToNextPhase() {
        when (status) {
            TimerStatus.WORK -> {
                status = TimerStatus.REST
                remainingSeconds = REST_DURATION_SECONDS
                playedEnd10 = false
                playPunchSound()
            }

            TimerStatus.REST -> {
                currentRound += 1
                status = TimerStatus.WORK
                remainingSeconds = WORK_DURATION_SECONDS
                playedEnd10 = false
                playStartSound()
            }
        }
    }

    private fun formatTime(totalSeconds: Int): String {
        val minutes = totalSeconds / 60
        val seconds = totalSeconds % 60
        return String.format("%02d:%02d", minutes, seconds)
    }

    private fun buildNotification(): Notification {
        val openAppIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val stateLabel = if (timerJob?.isActive == true) "RUN" else "PAUSE"
        val contentText = "$stateLabel · ${status.name}: ${formatTime(remainingSeconds)} · Раунд $currentRound"

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification() {
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.notify(NOTIFICATION_ID, buildNotification())
    }

    private fun broadcastState() {
        val stateIntent = Intent(ACTION_STATE_UPDATE).apply {
            putExtra(EXTRA_REMAINING_SECONDS, remainingSeconds)
            putExtra(EXTRA_ROUND, currentRound)
            putExtra(EXTRA_STATUS, status.name)
            putExtra(EXTRA_IS_RUNNING, timerJob?.isActive == true)
        }
        sendBroadcast(stateIntent)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Boxing timer",
                NotificationManager.IMPORTANCE_LOW
            )
            channel.description = "Foreground service channel for timer updates"
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun initPlayers() {
        startPlayer = MediaPlayer.create(this, R.raw.start)
        punchPlayer = MediaPlayer.create(this, R.raw.punch)
        end10Player = MediaPlayer.create(this, R.raw.end10)
    }

    private fun playStartSound() {
        startPlayer?.seekTo(0)
        startPlayer?.start()
    }

    private fun playPunchSound() {
        punchPlayer?.seekTo(0)
        punchPlayer?.start()
    }

    private fun playEnd10Sound() {
        end10Player?.seekTo(0)
        end10Player?.start()
    }

    private fun releasePlayers() {
        startPlayer?.release()
        punchPlayer?.release()
        end10Player?.release()
    }

    companion object {
        const val ACTION_START = "com.portal.boxingtimer.action.START"
        const val ACTION_PAUSE = "com.portal.boxingtimer.action.PAUSE"
        const val ACTION_RESET = "com.portal.boxingtimer.action.RESET"
        const val ACTION_STATE_UPDATE = "com.portal.boxingtimer.action.STATE_UPDATE"

        const val EXTRA_REMAINING_SECONDS = "extra_remaining_seconds"
        const val EXTRA_ROUND = "extra_round"
        const val EXTRA_STATUS = "extra_status"
        const val EXTRA_IS_RUNNING = "extra_is_running"

        private const val CHANNEL_ID = "boxing_timer_channel"
        private const val NOTIFICATION_ID = 101
        private const val WORK_DURATION_SECONDS = 3 * 60
        private const val REST_DURATION_SECONDS = 60
    }
}
