/**
 * Device location capture for delivery evidence. The hook returns raw device
 * metadata exactly as the GPS fix reported it (including accuracy and the
 * device clock) and never claims anti-spoofing guarantees — recorded signals
 * are contextual evidence only (docs/architecture/GEO_PHOTO_EVIDENCE.md).
 */

import { useCallback, useState } from "react";

export type DeviceLocationStatus = "IDLE" | "LOADING" | "CAPTURED" | "DENIED" | "UNAVAILABLE" | "TIMEOUT" | "ERROR";

export interface DeviceCoordinates {
  latitude: string;
  longitude: string;
  accuracy_m: string;
  timestamp: string;
  device_time: string;
}

export interface UseDeviceLocationResult {
  status: DeviceLocationStatus;
  coordinates: DeviceCoordinates | null;
  message: string | null;
  request: () => void;
}

const GEO_OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  timeout: 15_000,
  maximumAge: 5_000,
};

export function useDeviceLocation(): UseDeviceLocationResult {
  const [status, setStatus] = useState<DeviceLocationStatus>("IDLE");
  const [coordinates, setCoordinates] = useState<DeviceCoordinates | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const request = useCallback(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setStatus("UNAVAILABLE");
      setMessage("This device or browser cannot report a location. Submit with the location marked unavailable.");
      return;
    }
    setStatus("LOADING");
    setMessage(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        setCoordinates({
          // API/database coordinates use six decimal places (~0.11 m at the equator).
          latitude: latitude.toFixed(6),
          longitude: longitude.toFixed(6),
          accuracy_m: accuracy === null || accuracy === undefined ? "" : accuracy.toFixed(1),
          timestamp: new Date(position.timestamp).toISOString(),
          device_time: new Date(position.timestamp).toISOString(),
        });
        setStatus("CAPTURED");
        setMessage(null);
      },
      (error) => {
        switch (error.code) {
          case error.PERMISSION_DENIED:
            setStatus("DENIED");
            setMessage(
              "Location permission was denied. The submission will be stored without coordinates and reviewed accordingly.",
            );
            break;
          case error.POSITION_UNAVAILABLE:
            setStatus("UNAVAILABLE");
            setMessage("No location fix is available right now. Try again outdoors or submit without coordinates.");
            break;
          case error.TIMEOUT:
            setStatus("TIMEOUT");
            setMessage("Location capture timed out. Try again, or submit without coordinates.");
            break;
          default:
            setStatus("ERROR");
            setMessage("Location capture failed.");
        }
      },
      GEO_OPTIONS,
    );
  }, []);

  // No persistent watch: fixed point reads keep results inspectable and
  // predictable; the submission stores the single captured fix.

  return { status, coordinates, message, request };
}
