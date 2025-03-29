def speed_at_time(t, T, P, N, hold_fraction=0.1):
    """
    Returns the speed at a given time t for a smooth scroll-like motion profile.
    
    The motion is divided into three phases:
      1. Acceleration: from 0 to t_peak = T/N, using a smootherstep easing from 0 to P.
      2. Hold phase: from t_peak to hold_end, where speed is maintained at P.
      3. Deceleration: from hold_end to T, using a reversed smootherstep easing from P to 0.
      
    Args:
        t (float): The current time (0 <= t <= T).
        T (float): Total time duration.
        P (float): Peak speed.
        N (float): The peak is reached at T/N (i.e. t_peak = T/N).
        hold_fraction (float): Fraction of T used for the hold phase (default 0.2).
    
    Returns:
        float: The speed at time t.
    """
    t_peak = T / N
    hold_end = t_peak + hold_fraction * T
    
    def smootherstep(x):
        return 6*x**5 - 15*x**4 + 10*x**3
    
    if t <= t_peak:
        # Acceleration phase
        return P * smootherstep(t / t_peak)
    elif t <= hold_end:
        # Hold phase
        return P
    else:
        # Deceleration phase
        normalized = (t - hold_end) / (T - hold_end)
        return P * (1 - smootherstep(normalized))


# Example usage:
if __name__ == '__main__':
    import numpy as np
    import matplotlib.pyplot as plt

    T = 10    # Total duration
    P = 100   # Peak speed
    N = 5     # Peak is reached at T/N = 2 seconds
    num_points = 1000

    times = np.linspace(0, T, num_points)
    speeds = [speed_at_time(t, T, P, N) for t in times]

    plt.figure(figsize=(8, 5))
    plt.plot(times, speeds, label='Speed Profile', color='blue')
    plt.xlabel('Time')
    plt.ylabel('Speed')
    plt.title('Smooth Scroll-like Speed vs. Time Curve')
    plt.legend()
    plt.grid(True)
    plt.show()
