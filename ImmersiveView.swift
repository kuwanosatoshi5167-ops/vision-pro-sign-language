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
        RealityView { _ in
            /*
             今回はデータ収集だけを行うため、
             3Dオブジェクトは追加しない。
            */
        }
        .task {
            await recorder.startHandTrackingSession()
        }
    }
}
