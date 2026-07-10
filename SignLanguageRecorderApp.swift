//
//  SignLanguageRecorderApp.swift
//  SignLanguageRecorder
//
//  Created by satoshi kuwano on 2026/07/10.
//

import SwiftUI

@main
struct SignLanguageRecorderApp: App {

    @State private var recorder =
        HandTrackingRecorder()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(recorder)
        }

        ImmersiveSpace(id: "HandTrackingSpace") {
            ImmersiveView()
                .environment(recorder)
        }
        .immersionStyle(selection: .constant(.mixed), in: .mixed)
    }
}
