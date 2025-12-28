class Tank:
    def __init__(self, cap, fuel=0.0):
        if cap <= 0:
            raise ValueError("cap must be > 0")
        if fuel < 0:
            raise ValueError("fuel must be >= 0")
        self.cap = float(cap)
        self.fuel = min(float(fuel), self.cap)

    def fill(self, amt):
        if amt < 0:
            raise ValueError("amt must be >= 0")
        self.fuel = min(self.cap, self.fuel + float(amt))

    def take(self, amt):
        if amt < 0:
            raise ValueError("amt must be >= 0")
        got = min(self.fuel, float(amt))
        self.fuel -= got
        return got


class Eng:
    def __init__(self, rate):
        # liters per 100 km
        if rate <= 0:
            raise ValueError("rate must be > 0")
        self.rate = float(rate)

    def need(self, km):
        if km < 0:
            raise ValueError("km must be >= 0")
        return self.rate * float(km) / 100.0


class Whl:
    def __init__(self, n=4):
        self.n = int(n)

    def ok(self):
        return self.n == 4


class Car:
    def __init__(self, eng, tank, whl):
        # 组合：Car "has a" Eng/Tank/Whl
        self.eng = eng
        self.tank = tank
        self.whl = whl

    def fill(self, amt):
        self.tank.fill(amt)  # 委托

    def drive(self, km):
        # 高层能力：协调多个组件
        if not self.whl.ok():
            raise RuntimeError("wheel error")

        need = self.eng.need(km)
        got = self.tank.take(need)
        return got == need

    def fuel(self):
        return self.tank.fuel


if __name__ == "__main__":
    c = Car(Eng(6.5), Tank(50), Whl(4))
    c.fill(10)

    print("fuel:", c.fuel())  # 10.0
    print("drive 100km:", c.drive(100))  # True
    print("fuel:", c.fuel())  # 3.5
    print("drive 100km:", c.drive(100))  # False
    print("fuel:", c.fuel())  # 0.0
