from energy import home_energy_wh


def test_home_energy_normal():
    assert home_energy_wh(gep_wh=2000, imp_wh=500, exp_wh=300, car_ev_wh=400) == 1800


def test_home_energy_never_negative():
    assert home_energy_wh(gep_wh=100, imp_wh=0, exp_wh=500, car_ev_wh=0) == 0.0
