//
//  Untitled.swift
//  SignLanguageRecorder
//
//  Created by satoshi kuwano on 2026/07/10.
//

import ARKit

extension HandSkeleton.JointName {

    var csvName: String {
        switch self {
        case .forearmArm:
            return "forearmArm"

        case .forearmWrist:
            return "forearmWrist"

        case .wrist:
            return "wrist"

        case .thumbKnuckle:
            return "thumbKnuckle"

        case .thumbIntermediateBase:
            return "thumbIntermediateBase"

        case .thumbIntermediateTip:
            return "thumbIntermediateTip"

        case .thumbTip:
            return "thumbTip"

        case .indexFingerMetacarpal:
            return "indexFingerMetacarpal"

        case .indexFingerKnuckle:
            return "indexFingerKnuckle"

        case .indexFingerIntermediateBase:
            return "indexFingerIntermediateBase"

        case .indexFingerIntermediateTip:
            return "indexFingerIntermediateTip"

        case .indexFingerTip:
            return "indexFingerTip"

        case .middleFingerMetacarpal:
            return "middleFingerMetacarpal"

        case .middleFingerKnuckle:
            return "middleFingerKnuckle"

        case .middleFingerIntermediateBase:
            return "middleFingerIntermediateBase"

        case .middleFingerIntermediateTip:
            return "middleFingerIntermediateTip"

        case .middleFingerTip:
            return "middleFingerTip"

        case .ringFingerMetacarpal:
            return "ringFingerMetacarpal"

        case .ringFingerKnuckle:
            return "ringFingerKnuckle"

        case .ringFingerIntermediateBase:
            return "ringFingerIntermediateBase"

        case .ringFingerIntermediateTip:
            return "ringFingerIntermediateTip"

        case .ringFingerTip:
            return "ringFingerTip"

        case .littleFingerMetacarpal:
            return "littleFingerMetacarpal"

        case .littleFingerKnuckle:
            return "littleFingerKnuckle"

        case .littleFingerIntermediateBase:
            return "littleFingerIntermediateBase"

        case .littleFingerIntermediateTip:
            return "littleFingerIntermediateTip"

        case .littleFingerTip:
            return "littleFingerTip"

        @unknown default:
            return "unknown"
        }
    }
}
