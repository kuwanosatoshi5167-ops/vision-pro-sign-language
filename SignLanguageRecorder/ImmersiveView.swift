//
//  ImmersiveView.swift
//  SignLanguageRecorder
//
//  Created by satoshi kuwano on 2026/07/10.
//

import RealityKit
import SwiftUI

struct ImmersiveView: View {

    @Environment(HandTrackingRecorder.self)
    private var recorder

    var body: some View {
        RealityView { content in
            /*
             関節の球はサンプリングループが直接更新するため、
             ここではルートを追加するだけでよい。
            */
            content.add(recorder.visualizer.root)
        }
        .task {
            await recorder.startHandTrackingSession()
        }
        .onDisappear {
            recorder.stopHandTrackingSession()
        }
    }
}
