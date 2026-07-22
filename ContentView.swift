//
//  ContentView.swift
//  SignLanguageRecorder
//
//  Created by satoshi kuwano on 2026/07/10.
//

import SwiftUI

struct ContentView: View {

    @Environment(HandTrackingRecorder.self)
    private var recorder

    @Environment(\.openImmersiveSpace)
    private var openImmersiveSpace

    @Environment(\.dismissImmersiveSpace)
    private var dismissImmersiveSpace

    @State private var isImmersiveSpaceOpen = false

    var body: some View {
        @Bindable var recorder = recorder

        VStack(spacing: 20) {
            Image(systemName: "hand.raised.fingers.spread")
                .font(.system(size: 72))

            Text("Hand Joint Recorder")
                .font(.largeTitle)

            Text(recorder.statusMessage)
                .multilineTextAlignment(.center)

            LabeledContent(
                "Recorded CSV rows",
                value: "\(recorder.recordCount)"
            )

            if let savedFileURL = recorder.savedFileURL {
                VStack(spacing: 8) {
                    Text("Saved file")
                        .font(.headline)

                    Text(savedFileURL.lastPathComponent)
                        .font(.caption)
                        .textSelection(.enabled)
                }
            }

            Button(
                isImmersiveSpaceOpen
                    ? "Close Immersive Space"
                    : "Open Immersive Space"
            ) {
                Task {
                    await toggleImmersiveSpace()
                }
            }

            Button("Start Recording") {
                recorder.startRecording()
            }
            .disabled(
                !recorder.isSessionRunning
                || recorder.isRecording
            )

            Button("Stop and Save CSV") {
                recorder.stopRecordingAndSave()
            }
            .disabled(!recorder.isRecording)

            Button("Cancel Recording", role: .destructive) {
                recorder.cancelRecording()
            }
            .disabled(!recorder.isRecording)
        }
        .padding(40)
        .frame(width: 500)
    }

    private func toggleImmersiveSpace() async {
        if isImmersiveSpaceOpen {
            await dismissImmersiveSpace()
            isImmersiveSpaceOpen = false
        } else {
            let result = await openImmersiveSpace(
                id: "HandTrackingSpace"
            )

            switch result {
            case .opened:
                isImmersiveSpaceOpen = true

            case .userCancelled:
                recorder.statusMessage =
                    "Opening the immersive space was cancelled."

            case .error:
                recorder.statusMessage =
                    "Failed to open the immersive space."

            @unknown default:
                recorder.statusMessage =
                    "Unknown immersive-space result."
            }
        }
    }
}

#Preview {
    ContentView()
        .environment(HandTrackingRecorder())
}
