package com.portal.boxingtimer

import android.app.Service
import android.content.Intent
import android.os.IBinder

class TimerService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null
}
