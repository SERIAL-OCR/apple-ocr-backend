//
//  ContentView.swift
//  AppleSerialScanner
//
//  Created on Phase 2.2 - Multi-platform iOS/macOS Scanner
//

import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = SerialScannerViewModel()
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            SerialScannerView(viewModel: viewModel)
                .tabItem {
                    Label("Scan", systemImage: "camera")
                }
                .tag(0)

            HistoryView()
                .tabItem {
                    Label("History", systemImage: "clock")
                }
                .tag(1)

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .tag(2)
        }
        .onAppear {
            // Configure appearance for both iOS and macOS
            #if os(iOS)
            UITabBar.appearance().backgroundColor = UIColor.systemBackground
            #endif
        }
    }
}

#Preview {
    ContentView()
}